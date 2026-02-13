# Project State: Rogue Like RPG

## Project Reference
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** Procedural Map Features (Milestone 4)

## Current Position
**Phase:** 8 - Procedural Map Features
**Plan:** 01 (Complete)
**Status:** In Progress
**Progress Bar:** [█████░░░░░] 50%

## Performance Metrics
- **Engine:** esper ECS ✓
- **Combat:** Functional ✓
- **Navigation:** Nested World Architecture & World Map ✓
- **Persistence:** Entity Freeze/Thaw & Map Aging ✓
- **Visuals:** Selective Layer Rendering & Depth Effect ✓
- **Generation:** Procedural Buildings (Functional) ✓

## Accumulated Context
- **Decisions:** 
    - Render only layers <= player layer.
    - Darken lower layers by 0.3 per level difference.
    - Structural walls added to Village and House maps.
    - Ground sprites (e.g., '.', '#', 'X') act as occlusion layers, blocking rendering of layers below.
    - `add_house_to_map` automatically expands MapContainer layers and links them with Portals.
- **To Dos:**
    - Execute Phase 8 plan 08-02.
- **Blockers:** None.

## Session Continuity
- Last activity: 2026-02-13 - Completed 08-01-PLAN.md
- Resume file path: .planning/phases/08-procedural-map-features/08-02-PLAN.md
