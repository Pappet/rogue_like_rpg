---
phase: 03-core-gameplay-mechanics
plan: 03-03
subsystem: UI
tags: [ui, ecs, rendering]
depends_on: ["03-01"]
tech_stack: [pygame, esper]
key_files: [ecs/systems/ui_system.py, config.py, ecs/systems/render_system.py, services/render_service.py, components/camera.py]
---

# Phase 3 Plan 03: UI Header & Sidebar Summary

Built a persistent UI layout with a Header (Turn Info) and a Sidebar (Action List), integrating it into the ECS rendering pipeline with proper viewport management.

## Key Accomplishments

- **UI Framework:** Established a `UISystem` that manages layout and rendering of persistent UI elements.
- **Viewport Management:** Updated `Camera` and rendering systems (`RenderSystem`, `RenderService`) to support a clipped viewport, ensuring game world rendering doesn't overlap with UI areas.
- **Persistent Header:** Implemented a header that displays real-time "Global Round" and "Turn Status" (Player vs Environment).
- **Interactive Action Sidebar:** 
    - Created an `ActionList` ECS component to track available and selected actions.
    - Implemented a sidebar that visualizes the action list.
    - Added keyboard navigation (`W`/`S` keys) to browse through available actions.
    - Implemented visual feedback for selected and unavailable actions.

## Deviations from Plan

- **ActionList as Component:** Instead of just hardcoding actions in the `UISystem`, I implemented `ActionList` as a proper ECS component on the player entity to better align with the project's ECS architecture.

## Verification Results

- **Header Display:** Correctly shows "Round: X" and turn status with color coding.
- **Sidebar Display:** Correctly lists actions and highlights selection.
- **Map Alignment:** The map is correctly offset by `HEADER_HEIGHT` and limited by `SIDEBAR_WIDTH`, with no bleed-through into UI areas thanks to surface clipping.
- **Input Handling:** `W`/`S` keys correctly cycle through actions.

## Self-Check: PASSED
- [x] Header shows Round and Turn.
- [x] Sidebar shows Action List.
- [x] UI does not overlap with map rendering inappropriately.
- [x] All tasks committed.
