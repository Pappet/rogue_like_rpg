import random

import esper

from config import GameStates, LogCategory, SpriteLayer
from ecs.components import (
    AI,
    AIBehaviorState,
    AIState,
    Alignment,
    AttackIntent,
    Blocker,
    ChaseData,
    Corpse,
    EffectiveStats,
    Name,
    PathData,
    PlayerTag,
    Position,
    Stats,
)
from services.pathfinding_service import PathfindingService
from services.visibility_service import VisibilityService

CARDINAL_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # N S W E
LOSE_SIGHT_TURNS = 3


class AISystem(esper.Processor):
    """Explicit-call AI processor that owns enemy turn execution.

    Called once per frame by Game.update() when the turn state is ENEMY_TURN.
    Iterates all AI entities on the player's map layer, dispatches their
    behavior, and closes the enemy turn exactly once.
    """

    def __init__(self):
        super().__init__()

    def process(self, turn_system, map_container, player_layer, player_entity=None):
        """Run AI for all eligible entities and end the enemy turn.

        Guards:
          - Returns immediately if current state is not ENEMY_TURN (AISYS-01, AISYS-02).

        Entity filtering:
          - Skips entities on a different map layer than the player (SAFE-02).
          - Skips entities that carry a Corpse component (AISYS-05).

        Post-loop:
          - Calls turn_system.end_enemy_turn() exactly once (AISYS-04).
        """
        if turn_system.current_state != GameStates.ENEMY_TURN:
            return

        player_pos = None
        if player_entity is not None:
            player_pos = esper.try_component(player_entity, Position)

        claimed_tiles = set()  # Per-turn tile reservation (WNDR-04)

        # Use list() to avoid modification-during-iteration (matches movement_system.py pattern)
        for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
            # Skip entities not on the player's current map layer (SAFE-02)
            if pos.layer != player_layer:
                continue

            # Skip dead entities (AISYS-05)
            if esper.has_component(ent, Corpse):
                continue

            self._dispatch(ent, behavior, pos, map_container, claimed_tiles, player_pos)

        # End enemy turn unconditionally after all entity decisions (AISYS-04)
        turn_system.end_enemy_turn()

    def _dispatch(self, ent, behavior, pos, map_container, claimed_tiles, player_pos):
        """Dispatch entity to its current behavior handler.

        Detection block: before state dispatch, check if a HOSTILE NPC in WANDER/IDLE
        can see the player. If so, transition to CHASE and fire "notices you" message.
        The match statement then routes to the CHASE case naturally.
        """
        if behavior.state == AIState.SLEEP:
            return

        # Chase detection block (CHAS-01, CHAS-03, CHAS-04)
        if (
            behavior.alignment == Alignment.HOSTILE
            and player_pos is not None
            and behavior.state in (AIState.WANDER, AIState.IDLE)
        ):
            stats = esper.try_component(ent, Stats)
            if stats and self._can_see_player(pos, stats, player_pos, map_container, ent):
                behavior.state = AIState.CHASE
                esper.add_component(
                    ent,
                    ChaseData(
                        last_known_x=player_pos.x,
                        last_known_y=player_pos.y,
                    ),
                )
                name_comp = esper.try_component(ent, Name)
                if name_comp:
                    esper.dispatch_event("log_message", f"The {name_comp.name} notices you!", None, LogCategory.ALERT)
                else:
                    esper.dispatch_event("log_message", "Something notices you!", None, LogCategory.ALERT)

        # PathData Priority (Task 1)
        # Note: CHASE state manages its own PathData to handle moving targets.
        if behavior.state != AIState.CHASE and esper.has_component(ent, PathData):
            path_data = esper.component_for_entity(ent, PathData)
            if self._try_follow_path(ent, path_data, pos, claimed_tiles):
                return

        match behavior.state:
            case AIState.IDLE:
                pass  # No-op: idle entities do nothing
            case AIState.WANDER:
                self._wander(ent, pos, map_container, claimed_tiles)
            case AIState.CHASE:
                self._chase(ent, behavior, pos, map_container, claimed_tiles, player_pos)
            case AIState.TALK:
                pass  # Stub: talk behavior implemented later
            case AIState.WORK | AIState.PATROL | AIState.SOCIALIZE | AIState.SLEEP:
                pass  # Handled by ScheduleSystem + PathData Priority

    def _wander(self, ent, pos, map_container, claimed_tiles):
        """Move entity randomly to a walkable, unoccupied adjacent cardinal tile.

        WNDR-01: Cardinal directions only.
        WNDR-02: Tile must be walkable and free of blockers.
        WNDR-03: Skip turn if no valid tile found — no error.
        WNDR-04: claimed_tiles prevents two NPCs targeting same destination.
        """
        dirs = CARDINAL_DIRS[:]
        random.shuffle(dirs)
        for dx, dy in dirs:
            nx, ny = pos.x + dx, pos.y + dy
            if (nx, ny) in claimed_tiles:
                continue  # WNDR-04: already claimed this turn
            if not self._is_walkable(nx, ny, pos.layer, map_container):
                continue  # WNDR-02: tile not walkable
            if self._get_blocker_at(nx, ny, pos.layer):
                continue  # WNDR-02: entity blocking tile
            # Valid destination found — claim and move
            claimed_tiles.add((nx, ny))
            pos.x = nx
            pos.y = ny
            return
        # WNDR-03: No valid tile — entity skips turn silently

    def _chase(self, ent, behavior, pos, map_container, claimed_tiles, player_pos):
        """Move NPC toward last known player position using PathfindingService (A*).

        CHAS-02: Pathfinding step per turn toward target.
        CHAS-05: After LOSE_SIGHT_TURNS without LOS, revert to WANDER.
        """
        chase_data = esper.try_component(ent, ChaseData)
        if not chase_data:
            # ChaseData missing — malformed state; revert to WANDER
            behavior.state = AIState.WANDER
            return

        stats = esper.try_component(ent, Stats)
        # Sight check: update last_known position or increment lose-sight counter
        if player_pos is not None and stats is not None:
            if self._can_see_player(pos, stats, player_pos, map_container, ent):
                chase_data.last_known_x = player_pos.x
                chase_data.last_known_y = player_pos.y
                chase_data.turns_without_sight = 0
            else:
                chase_data.turns_without_sight += 1
                if chase_data.turns_without_sight >= LOSE_SIGHT_TURNS:
                    behavior.state = AIState.WANDER
                    esper.remove_component(ent, ChaseData)
                    if esper.has_component(ent, PathData):
                        esper.remove_component(ent, PathData)
                    return
        else:
            # No player_pos available — increment counter
            chase_data.turns_without_sight += 1
            if chase_data.turns_without_sight >= LOSE_SIGHT_TURNS:
                behavior.state = AIState.WANDER
                esper.remove_component(ent, ChaseData)
                if esper.has_component(ent, PathData):
                    esper.remove_component(ent, PathData)
                return

        # Pathfinding logic (Task 1 & 2)
        target_pos = (chase_data.last_known_x, chase_data.last_known_y)

        path_data = None
        if esper.has_component(ent, PathData):
            path_data = esper.component_for_entity(ent, PathData)

        # Destination Invalidation: Recompute if destination changed or no path exists
        if path_data is None or path_data.destination != target_pos or not path_data.path:
            path = PathfindingService.get_path(esper, map_container, (pos.x, pos.y), target_pos, pos.layer)
            if path:
                if path_data:
                    path_data.path = path
                    path_data.destination = target_pos
                else:
                    path_data = PathData(path=path, destination=target_pos)
                    esper.add_component(ent, path_data)
            else:
                # Fallback to greedy Manhattan if A* fails
                self._greedy_step(ent, pos, target_pos, map_container, claimed_tiles)
                return

        # Try to follow the path (Task 1)
        if not self._try_follow_path(ent, path_data, pos, claimed_tiles):
            # If path failed (blocked), attempt greedy fallback
            self._greedy_step(ent, pos, target_pos, map_container, claimed_tiles)

    def _greedy_step(self, ent, pos, target_pos, map_container, claimed_tiles):
        """Move entity one step toward target using greedy Manhattan distance.

        Used as a fallback when pathfinding fails or path is blocked.
        """
        tx, ty = target_pos
        dx = tx - pos.x
        dy = ty - pos.y

        # Build candidate list: prefer axis with larger abs delta first
        if abs(dx) >= abs(dy):
            candidates = []
            if dx != 0:
                candidates.append((1 if dx > 0 else -1, 0))
            if dy != 0:
                candidates.append((0, 1 if dy > 0 else -1))
        else:
            candidates = []
            if dy != 0:
                candidates.append((0, 1 if dy > 0 else -1))
            if dx != 0:
                candidates.append((1 if dx > 0 else -1, 0))

        for step_x, step_y in candidates:
            nx, ny = pos.x + step_x, pos.y + step_y
            if (nx, ny) in claimed_tiles:
                continue
            if not self._is_walkable(nx, ny, pos.layer, map_container):
                continue
            blocker_ent = self._get_blocker_at(nx, ny, pos.layer)
            if blocker_ent:
                if esper.has_component(blocker_ent, PlayerTag):
                    esper.add_component(ent, AttackIntent(target_entity=blocker_ent))
                    return True  # Turn consumed by attack
                continue
            # Valid step found — claim and move
            claimed_tiles.add((nx, ny))
            pos.x = nx
            pos.y = ny
            return True
        return False

    def _try_follow_path(self, ent, path_data, pos, claimed_tiles):
        """Attempts to take the next step in the precomputed path.

        Returns True if a step was taken, False if blocked or empty.
        Invalidates (clears) the path if it's blocked by an entity.
        """
        if not path_data.path:
            return False

        nx, ny = path_data.path[0]

        if (nx, ny) in claimed_tiles:
            return False

        blocker_ent = self._get_blocker_at(nx, ny, pos.layer)
        if blocker_ent:
            if esper.has_component(blocker_ent, PlayerTag):
                esper.add_component(ent, AttackIntent(target_entity=blocker_ent))
                path_data.path = []  # Invalidate after attack
                return True  # Turn consumed by attack
            # Blocked by non-player entity — invalidate path
            path_data.path = []
            return False

        # Move
        path_data.path.pop(0)
        claimed_tiles.add((nx, ny))
        pos.x = nx
        pos.y = ny
        return True

    def _can_see_player(self, pos, stats, player_pos, map_container, ent=None):
        """Returns True if NPC at pos can see player_pos using FOV computation."""
        is_transparent = self._make_transparency_func(pos.layer, map_container)

        radius = stats.perception
        if ent is not None and esper.has_component(ent, EffectiveStats):
            radius = esper.component_for_entity(ent, EffectiveStats).perception

        visible = VisibilityService.compute_visibility((pos.x, pos.y), radius, is_transparent)
        return (player_pos.x, player_pos.y) in visible

    def _make_transparency_func(self, layer_idx, map_container):
        """Build transparency function for VisibilityService — mirrors visibility_system.py pattern."""

        def is_transparent(x, y):
            if 0 <= layer_idx < len(map_container.layers):
                layer = map_container.layers[layer_idx]
                if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                    tile = layer.tiles[y][x]
                    if not tile.transparent:
                        return False
                    return tile.sprites.get(SpriteLayer.GROUND) != "#"
            return False

        return is_transparent

    def _is_walkable(self, x, y, layer_idx, map_container):
        """Returns True if tile at (x, y, layer_idx) exists and is walkable."""
        tile = map_container.get_tile(x, y, layer_idx)
        return tile.walkable if tile else False

    def _get_blocker_at(self, x, y, layer_idx):
        """Returns entity ID of the Blocker at (x, y, layer_idx), or None."""
        for ent, (pos, blocker) in esper.get_components(Position, Blocker):
            if pos.x == x and pos.y == y and pos.layer == layer_idx:
                return ent
        return None
