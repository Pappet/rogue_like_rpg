import random

import esper
from config import GameStates
from ecs.components import AI, AIBehaviorState, Blocker, Corpse, Position, AIState

CARDINAL_DIRS = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # N S W E


class AISystem(esper.Processor):
    """Explicit-call AI processor that owns enemy turn execution.

    Called once per frame by Game.update() when the turn state is ENEMY_TURN.
    Iterates all AI entities on the player's map layer, dispatches their
    behavior, and closes the enemy turn exactly once.
    """

    def __init__(self):
        super().__init__()

    def process(self, turn_system, map_container, player_layer):
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

        claimed_tiles = set()  # Per-turn tile reservation (WNDR-04)

        # Use list() to avoid modification-during-iteration (matches movement_system.py pattern)
        for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
            # Skip entities not on the player's current map layer (SAFE-02)
            if pos.layer != player_layer:
                continue

            # Skip dead entities (AISYS-05)
            if esper.has_component(ent, Corpse):
                continue

            self._dispatch(ent, behavior, pos, map_container, claimed_tiles)

        # End enemy turn unconditionally after all entity decisions (AISYS-04)
        turn_system.end_enemy_turn()

    def _dispatch(self, ent, behavior, pos, map_container, claimed_tiles):
        """Dispatch entity to its current behavior handler."""
        match behavior.state:
            case AIState.IDLE:
                pass  # No-op: idle entities do nothing
            case AIState.WANDER:
                self._wander(ent, pos, map_container, claimed_tiles)
            case AIState.CHASE:
                pass  # Stub: chase behavior implemented in phase 18
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
