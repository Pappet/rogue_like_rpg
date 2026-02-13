# Plan 04-04 Summary

## Status: Complete
**Plan:** 04-04-PLAN.md
**Tasks:** 2/2

## Achievements
- Implemented `DeathSystem` in `ecs/systems/death_system.py` which listens for `entity_died` events.
- Added `Corpse` tag component in `ecs/components.py`.
- Connected the combat loop to the death system: when an entity's HP drops to zero (handled in `CombatSystem`), an `entity_died` event is dispatched.
- The `DeathSystem` correctly transforms the entity:
    - Logs a message (e.g., "[color=orange]Orc[/color] dies!").
    - Removes `Blocker`, `AI`, and `Stats` components so the entity no longer participates in gameplay or blocks movement.
    - Updates the `Renderable` component to display a corpse sprite ("%") in dark red on the `CORPSES` layer.
    - Adds the `Corpse` component for identification.

## Artifacts
- `ecs/systems/death_system.py`: Contains the `DeathSystem` class and `on_entity_died` handler.
- `ecs/components.py`: Updated with `Corpse` component.

## Verification
- Verified that killing a monster results in a corpse that can be walked over.
- Verified that the death message appears in the log.
