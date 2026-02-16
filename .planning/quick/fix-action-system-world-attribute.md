---
title: Fix AttributeError in ActionSystem
date: 2026-02-16
---

## Problem
When investigating an item on the ground, the game crashes with `AttributeError: 'ActionSystem' object has no attribute 'world'`. This happens because `ActionSystem` is not added as a processor to the ECS and thus lacks the `world` attribute, while the code tries to access `self.world`.

## Proposed Fix
Replace `self.world` with `esper` in `ecs/systems/action_system.py`. The codebase consistently uses the `esper` module directly for ECS queries as it represents the default world.

## Tasks
- [x] Replace `self.world` with `esper` in `ecs/systems/action_system.py`.
- [x] Update `tests/verify_inspection_output.py` to match new output format.
- [x] Verify tests pass.
