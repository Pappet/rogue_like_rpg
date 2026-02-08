# User Acceptance Testing (UAT) for Phase 2: Core Gameplay Loop

This document records the results of user acceptance testing for Phase 2.

## Test Results

| Test | Description | Status | Notes |
|---|---|---|---|
| 1 | The game world is represented by a grid of tiles. | PASS | User confirmed seeing a grid of tiles. |
| 2 | The game progresses in turns. | PASS | Verified via terminal output cycling between Player and Enemy turns. |
| 3 | The player controls a party of up to 3 heroes that move as a single unit. | PASS | User confirmed party moves as one unit. |
| 4 | The game uses sprite-based graphics with multiple layers. | PASS | User confirmed seeing entities (like 'T') on top of tiles. |
| 5 | The tile size is configurable. | PASS | User confirmed representation is proportional and correct. |

## Issues Found & Resolved

1. **AttributeError: 'Camera' object has no attribute 'update'**:
   - **Diagnosis**: The `Camera` class was missing the `update` method called in `game_states.py`.
   - **Fix**: Implemented `Camera.update(target_x, target_y)` to center the view on the player.
2. **Turn Cycling Logic**:
   - **Diagnosis**: `TurnService` was initially set to always return `PLAYER_TURN` and didn't cycle to `ENEMY_TURN`.
   - **Fix**: Updated `TurnService` to cycle states and implemented a basic automatic skip for the enemy turn in `Game.update`.

## Summary

All success criteria for Phase 2 have been met and verified by the user. The project is ready to move to Phase 3.
