import esper
from config import GameStates
from ecs.components import AI, AIBehaviorState, Corpse, Position, AIState


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

        # Use list() to avoid modification-during-iteration (matches movement_system.py pattern)
        for ent, (ai, behavior, pos) in list(esper.get_components(AI, AIBehaviorState, Position)):
            # Skip entities not on the player's current map layer (SAFE-02)
            if pos.layer != player_layer:
                continue

            # Skip dead entities (AISYS-05)
            if esper.has_component(ent, Corpse):
                continue

            self._dispatch(ent, behavior, pos)

        # End enemy turn unconditionally after all entity decisions (AISYS-04)
        turn_system.end_enemy_turn()

    def _dispatch(self, ent, behavior, pos):
        """Dispatch entity to its current behavior handler.

        All handlers are stubs in the skeleton; concrete behavior is added
        in later phases (WANDER phase 17, CHASE phase 18).
        """
        match behavior.state:
            case AIState.IDLE:
                pass  # No-op: idle entities do nothing
            case AIState.WANDER:
                pass  # Stub: wander behavior implemented in phase 17
            case AIState.CHASE:
                pass  # Stub: chase behavior implemented in phase 18
            case AIState.TALK:
                pass  # Stub: talk behavior implemented later
