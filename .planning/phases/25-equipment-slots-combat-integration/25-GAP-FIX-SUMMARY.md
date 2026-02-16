# Phase 25 Plan GAP-FIX: Critical Bug Fixes Summary

## One-liner
Fixed malformed UISystem code and updated CombatSystem to correctly handle HP bonuses in death checks.

## Tech Stack
- Python
- Esper (ECS)
- Pygame

## Key Files
- ecs/systems/ui_system.py: Moved is_action_available to class method and fixed indentation.
- ecs/systems/combat_system.py: Updated death check to use EffectiveStats.hp and avoid stale data.

## Deviations from Plan
- Fixed a potential bug in CombatSystem where death checks would use stale EffectiveStats.hp data by manually updating it after damage is applied.

## Self-Check: PASSED
- [x] UISystem doesn't crash on sidebar render (verified via instantiation and method call test).
- [x] Combat death check accounts for equipment HP bonuses (verified via unit test).

## Commits
- ed7ed9d: fix(25-GAP-FIX): move is_action_available to UISystem class method
- 4a3bc29: fix(25-GAP-FIX): update death check to use effective HP
