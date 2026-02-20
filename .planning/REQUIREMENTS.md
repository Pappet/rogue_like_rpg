# Requirements: Rogue Like RPG — v1.6 UI/UX Architecture & Input Overhaul

**Defined:** 2026-02-20
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat. "Presentation and interaction layers must be modular, scalable, and player-friendly."

## v1.6 Requirements

Requirements for v1.6 milestone. Each maps to roadmap phases.

### Modular UI Foundation
- **UI-MOD-01**: Refactor `UISystem` to eliminate magic numbers for layout.
- **UI-MOD-02**: Implement a dynamic layout cursor (Y-cursor) for vertical element stacking.
- **UI-MOD-03**: Decompose monolithic draw methods into isolated render functions (Header, Sidebar, MessageLog).
- **UI-MOD-04**: Standardize UI constants (padding, margins, colors) in `config.py`.

### Unified Input System
- **INP-01**: Centralize input handling in an `InputManager` or similar component.
- **INP-02**: Implement context-sensitive "Bump-to-Action" (Attack hostile, Interaction/Talk neutral).
- **INP-03**: Support "Hotbar" style selection for special actions via number keys (1-9).
- **INP-04**: Map keyboard keys to high-level commands (NAVIGATE_UP, CONFIRM, CANCEL) to decouple from raw keycodes.

### Stateful Menu Overlays
- **MENU-01**: Implement a stateful Window/Modal system for full-screen or focused interactions.
- **MENU-02**: Create `InventoryScreen` modal that replaces the sidebar-based inventory listing.
- **MENU-03**: Create `CharacterScreen` modal for detailed stats and equipment overview.
- **MENU-04**: Implement a UI Stack where modals capture input first, pausing the game world if necessary.

### Visual Feedback & Polish
- **FEED-01**: Implement Floating Combat Text (FCT) for damage and status effect indicators on the map.
- **FEED-02**: Categorize message log entries by color (e.g., Red for damage taken, Gold for loot).
- **FEED-03**: Improve viewport real estate by moving low-priority info from permanent HUD to modals.
- **FEED-04**: Add "Examine" mode tooltips or hover details for entities/items.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Mouse-driven UI interaction | Keyboard-first design for v1.6; mouse-support deferred to v1.8 |
| Animation system | Basic FCT only; full entity animations are v1.9 |
| Controller support | Focus on Keyboard/Mouse first |
| Save/Load Menu | Persistence milestone not yet planned |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| UI-MOD-01, UI-MOD-02, UI-MOD-03, UI-MOD-04 | Phase 33 | Pending |
| INP-01, INP-02, INP-03, INP-04 | Phase 34 | Pending |
| MENU-01, MENU-02, MENU-03, MENU-04 | Phase 35 | Pending |
| FEED-01, FEED-02, FEED-03, FEED-04 | Phase 36 | Pending |

---
*Requirements defined: 2026-02-20*
