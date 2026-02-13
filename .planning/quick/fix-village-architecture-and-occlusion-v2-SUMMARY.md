---
phase: quick
plan: fix-village-architecture-and-occlusion-v2
subsystem: rendering
tags: [village, occlusion, layers, map]
key-files:
  - services/map_service.py
  - services/render_service.py
  - ecs/systems/render_system.py
---

# Quick Fix: Village Architecture and Occlusion V2

## Plan Summary
Refined the Village architecture with a multi-layered house (walls, roof, balcony) and implemented ground-occlusion rendering logic to enhance depth perception.

## Key Changes
1.  **Village Map Refactor:**
    -   Moved house walls to Layer 1.
    -   Added house roof on Layer 2 (occludes interior).
    -   Added balcony on Layer 2 (occludes ground below it, but allows seeing surrounding ground from high vantage).
    -   Updated portal positions and logic to match new structure.
2.  **Occlusion Rendering (Map):**
    -   Updated `RenderService.render_map` to search downwards from `player_layer`.
    -   Rendering stops at the first layer with a `SpriteLayer.GROUND` sprite, treating it as the opaque base.
    -   This allows players on high layers (e.g., balcony) to see the ground far below, while roof/floors block what's directly underneath.
3.  **Occlusion Rendering (Entities):**
    -   Updated `RenderSystem.process` to hide entities if they are covered by a `SpriteLayer.GROUND` sprite on a higher layer (up to `player_layer`).

## Visual Effect
-   **On Ground (Layer 0):** Player sees surrounding ground. House interior is separate map.
-   **On Balcony (Layer 2):** Player sees balcony floor. Surrounding area shows ground (Layer 0) darkened by depth factor (0.4 opacity).
-   **On Roof (Layer 2):** Player sees roof. Interior (if it were on Layer 1/0 of same map) would be hidden.

## Deviations
None.

## Verification
-   **Architecture:** Village has 3 layers; House has 2 layers.
-   **Occlusion:** Code inspection confirms occlusion logic correctly identifies base layer and hides obscured entities.
-   **Portals:** Portals align with the new physical structure (Door at wall gap, Balcony connected to upper floor).

## Self-Check: PASSED
-   Created/Modified files exist.
-   Logic implemented as requested.
