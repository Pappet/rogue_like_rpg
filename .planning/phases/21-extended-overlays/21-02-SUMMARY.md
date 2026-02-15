# Phase 21 Plan 02: Chase Vectors and Sight Counters Summary

Enhanced the debug overlay with visual indicators for NPC chase behavior and memory.

## Subsystem: Debug Overlays
- **Subsystem:** Debug
- **Wave:** 2
- **Tags:** Visualization, AI, Debug

## Key Changes

### Implement Chase Vector Vectors
- Updated `DebugRenderSystem._render_chase_targets` to draw a line from the NPC to its last known target position.
- Added a circle and tile outline at the target position to clearly mark the NPC's destination.
- Implemented off-screen culling for performance optimization.

### Enhance AI Labels with Sight Counter
- Updated `DebugRenderSystem._render_ai_labels` to include a turn counter (`T:X`) for entities with `ChaseData`.
- This provides real-time feedback on how many turns an NPC has been without line-of-sight to its target.

## Tech Stack
- **Pygame:** Used `pygame.draw.line`, `pygame.draw.circle`, and `pygame.draw.rect`.
- **Esper:** Utilized `get_components`, `has_component`, and `component_for_entity`.

## Key Files
- `ecs/systems/debug_render_system.py`: Primary implementation site for debug visualizations.

## Deviations from Plan
- None - plan executed exactly as written.

## Self-Check: PASSED
1. [x] `ecs/systems/debug_render_system.py` contains `_render_chase_targets` with line and circle drawing.
2. [x] `ecs/systems/debug_render_system.py` contains `_render_ai_labels` with `turns_without_sight` display.
3. [x] All changes committed with proper prefixes.
