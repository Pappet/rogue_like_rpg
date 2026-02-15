---
phase: 21-extended-overlays
plan: 01
subsystem: Debug Overlay
tags: [debug, ui, input]
requires: [20-01]
provides: [granular-debug-control]
tech-stack: [pygame, esper]
key-files: [config.py, game_states.py, ecs/systems/debug_render_system.py]
decisions:
  - Migrated debug_enabled boolean to debug_flags dictionary for granular control.
  - Linked debug sub-toggles (F4-F7) to the master toggle (F3).
metrics:
  duration: 15min
  completed_date: 2026-02-15T15:00:00Z
---

# Phase 21 Plan 01: Granular Debug Control Summary

Implemented a granular debug overlay system that allows developers to toggle specific categories of debug information independently.

## Key Changes

### Configuration
- Added `DEBUG_NPC_FOV_COLOR`, `DEBUG_ARROW_COLOR`, and `DEBUG_TEXT_BG_COLOR` to `config.py`.

### Input Handling
- Refactored `Game.startup` to initialize and migrate `debug_flags`.
- Updated `Game.handle_player_input` to support:
  - **F3**: Master Debug Toggle
  - **F4**: Player FOV Toggle
  - **F5**: NPC FOV Toggle
  - **F6**: Chase Toggle
  - **F7**: AI Labels Toggle
- Sub-toggles only work when Master Debug is enabled.

### Rendering
- Updated `DebugRenderSystem.process` to accept a flags dictionary.
- The system now conditionally renders FOV, Chase markers, and AI labels based on the active flags.
- Added `_render_npc_fov` placeholder method.

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
1. Created files exist: N/A (Modified only)
2. Commits exist:
   - 238b6cb: feat(21-01): add new debug colors to configuration
   - 4cb11e0: refactor(21-01): update debug input handling and flags
   - be2eb28: feat(21-01): update DebugRenderSystem to respect flags
