import random

import esper
from config import GameStates, SpriteLayer
from ecs.components import AI, AIBehaviorState, Blocker, Corpse, Position, AIState, ChaseData, Name, Stats, Alignment
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
            try:
                player_pos = esper.component_for_entity(player_entity, Position)
            except KeyError:
                pass

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
        # Chase detection block (CHAS-01, CHAS-03, CHAS-04)
        if (
            behavior.alignment == Alignment.HOSTILE
            and player_pos is not None
            and behavior.state in (AIState.WANDER, AIState.IDLE)
        ):
            try:
                stats = esper.component_for_entity(ent, Stats)
                if self._can_see_player(pos, stats, player_pos, map_container):
                    behavior.state = AIState.CHASE
                    esper.add_component(ent, ChaseData(
                        last_known_x=player_pos.x,
                        last_known_y=player_pos.y,
                    ))
                    try:
                        name = esper.component_for_entity(ent, Name)
                        esper.dispatch_event("log_message", f"The {name.name} notices you!")
                    except KeyError:
                        esper.dispatch_event("log_message", "Something notices you!")
            except KeyError:
                pass  # NPC has no Stats — cannot use perception for detection

        match behavior.state:
            case AIState.IDLE:
                pass  # No-op: idle entities do nothing
            case AIState.WANDER:
                self._wander(ent, pos, map_container, claimed_tiles)
            case AIState.CHASE:
                self._chase(ent, behavior, pos, map_container, claimed_tiles, player_pos)
            case AIState.TALK:
                pass  # Stub: talk behavior implemented later

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
        """Move NPC toward last known player position using greedy Manhattan step.

        CHAS-02: One greedy Manhattan step per turn toward target.
        CHAS-05: After LOSE_SIGHT_TURNS without LOS, revert to WANDER.
        """
        try:
            chase_data = esper.component_for_entity(ent, ChaseData)
        except KeyError:
            # ChaseData missing — malformed state; revert to WANDER
            behavior.state = AIState.WANDER
            return

        try:
            stats = esper.component_for_entity(ent, Stats)
        except KeyError:
            stats = None

        # Sight check: update last_known position or increment lose-sight counter
        if player_pos is not None and stats is not None:
            if self._can_see_player(pos, stats, player_pos, map_container):
                chase_data.last_known_x = player_pos.x
                chase_data.last_known_y = player_pos.y
                chase_data.turns_without_sight = 0
            else:
                chase_data.turns_without_sight += 1
                if chase_data.turns_without_sight >= LOSE_SIGHT_TURNS:
                    behavior.state = AIState.WANDER
                    esper.remove_component(ent, ChaseData)
                    return
        else:
            # No player_pos available — increment counter
            chase_data.turns_without_sight += 1
            if chase_data.turns_without_sight >= LOSE_SIGHT_TURNS:
                behavior.state = AIState.WANDER
                esper.remove_component(ent, ChaseData)
                return

        # Greedy Manhattan step toward last known position (CHAS-02)
        tx, ty = chase_data.last_known_x, chase_data.last_known_y
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
            if step_x == 0 and step_y == 0:
                continue
            nx, ny = pos.x + step_x, pos.y + step_y
            if (nx, ny) in claimed_tiles:
                continue
            if not self._is_walkable(nx, ny, pos.layer, map_container):
                continue
            if self._get_blocker_at(nx, ny, pos.layer):
                continue  # Player tile has Blocker — NPC stays adjacent
            # Valid step found — claim and move
            claimed_tiles.add((nx, ny))
            pos.x = nx
            pos.y = ny
            return
        # No valid step — NPC stays in place this turn

    def _can_see_player(self, pos, stats, player_pos, map_container):
        """Returns True if NPC at pos can see player_pos using FOV computation."""
        is_transparent = self._make_transparency_func(pos.layer, map_container)
        visible = VisibilityService.compute_visibility(
            (pos.x, pos.y), stats.perception, is_transparent
        )
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
                    if tile.sprites.get(SpriteLayer.GROUND) == "#":
                        return False
                    return True
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
