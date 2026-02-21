# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-20)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.6 UI/UX Architecture & Input Overhaul — Infrastructure

## Current Position

Phase: 36 of 36 (Feedback & Information Hierarchy)
Plan: 3 of 3 in current phase
Status: Milestone Complete
Last activity: 2026-02-21 — Completed Phase 36 and Milestone v1.6.

Progress: [██████████] 100% (Phase 36) / 100% (v1.6)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.6): 12
- Average duration: 15m
- Total execution time: 180m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 33 | 3 | 30m | 10m |
| 34 | 3 | 30m | 10m |
| 35 | 3 | 75m | 25m |
| 36 | 3 | 45m | 15m |

**Recent Trend:** Milestone v1.6 complete. UI/UX is now modular, responsive, and provides rich feedback (FCT, tooltips, categorized logs).

## Quick Tasks Completed

| Task | Description | Date |
|------|-------------|------|
| hotbar-fixes | Fix hotbar 6, prioritize portal 'Enter'/'INTERACT' | 2026-02-21 |
| v1.6-TD | Fix input leaks and centralize UI constants | 2026-02-21 |
| 36-03 | Implement Examine Mode and Tooltips | 2026-02-21 |
| 36-02 | Categorize Message Log and implement low-health alerts | 2026-02-21 |
| 36-01 | Implement Floating Combat Text (FCT) system | 2026-02-21 |
| 35-03 | Viewport Expansion and HUD Refactor | 2026-02-21 |
| 35-02 | Implement Inventory and Character sheet modals | 2026-02-21 |
| 35-01 | Implement UIStack and UIWindow infrastructure | 2026-02-21 |
| 34-03 | Implement Hotbar Action Selection (1-9) | 2026-02-20 |
| 34-02 | Implement Context-Sensitive "Bump" Interactions | 2026-02-20 |
| 34-01 | Implement InputManager and centralized command mapping | 2026-02-20 |
| 33-03 | Verify modular UI, add 'Needs' section, increase resolution | 2026-02-20 |
| 33-02 | Refactor UI Rendering into Modular Functions | 2026-02-20 |
| 33-01 | Add UI Layout Infrastructure (constants & cursor) | 2026-02-20 |
| v1.6-INIT | Initialize v1.6 Requirements and Roadmap | 2026-02-20 |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- **Modular UI:** UI elements decoupled from `ui_system.py` into distinct render functions with a dynamic Y-cursor for layout.
- **Stateful Modals:** Transition from full-state screens to event-driven overlays that can be stacked.
- **Bump-to-Action:** Primary interaction method for basic combat and NPC interaction.
- **UI Infrastructure:** Established UI constants and `LayoutCursor` for dynamic stacking.
- **Relative Positioning:** Header elements use relative positioning based on `header_rect` boundaries and `UI_PADDING`.
- **Increased Resolution:** Decision to use 1280x720 as the base resolution for better visibility.
- **Dynamic Header:** Header uses a horizontal cursor to prevent text overlaps.
- **Centralized Input:** Input handled by dedicated `InputManager` mapping keys to commands based on state.
- **Hotbar Slots:** Player has `HotbarSlots` component mapping keys 1-9 to specific `Action` objects for quick execution.
- **Contextual Bump:** Collisions automatically resolve to Attack, Wake Up, or Talk based on target components.
- **UI Stack Architecture:** Centralized `UIStack` manager handles modal lifecycles (Inventory, Character, Tooltips).
- **Viewport Expansion:** Reclaimed sidebar space (220px) for the game world. Viewport width is now full screen width.
- **Floating Combat Text (FCT):** Entity-based FCT system with fading and upward movement for immediate feedback.
- **Log Categorization:** Messages are now color-coded by category (Damage, Healing, Loot, Alerts).
- **Examine Mode:** Dedicated inspection mode with a cursor and detailed modal tooltips.
- **Quick Transitions:** Reduced house entry/exit time to 1 tick for smoother exploration.
- **Portal Interaction Priority:** Pressing 'Enter' or 'g' while standing on a portal takes priority over other actions, improving UX for transitions.
- **Hotbar 6 Mapping:** Explicitly mapped Hotbar 6 to open the Inventory modal for consistent quick-access.
- **Input Consumption:** Modal UI windows (Inventory, Character) consume all KEYDOWN events to prevent background leakage.
- **Centralized UI Colors:** Magic numbers for UI colors and basic spacing centralized in `config.py`.

### Pending Todos

- [ ] Milestone v1.7 Planning (Dungeon Progression / Leveling).

### Blockers/Concerns

- **Performance:** monitor impact of many FCT entities during large battles.
