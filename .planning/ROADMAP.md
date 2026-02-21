# Project Roadmap: Rogue Like RPG

## Milestones

- ✅ **v1.0 MVP** — Phases 1-11 (shipped 2026-02-14)
- ✅ **v1.1 Investigation System** — Phases 12-14 (shipped 2026-02-14)
- ✅ **v1.2 AI Infrastructure** — Phases 15-18 (shipped 2026-02-15)
- ✅ **v1.3 Debug Overlay System** — Phases 19-22 (shipped 2026-02-15)
- ✅ **v1.4 Item & Inventory System** — Phases 23-26 (shipped 2026-02-16)
- ✅ **v1.5 World Clock & NPC Schedules** — Phases 27-32 (shipped 2026-02-20)
- ✅ **v1.6 UI/UX Architecture & Input Overhaul** — Phases 33-36 (shipped 2026-02-21)

---

## ✅ v1.6 UI/UX Architecture & Input Overhaul

**Milestone Goal:** Refactor the presentation and interaction layers to be modular, scalable, and player-friendly.

**Coverage:** UI-MOD-01 to UI-MOD-04, INP-01 to INP-04, MENU-01 to MENU-04, FEED-01 to FEED-04.

---

### Phase 33: UI Rendering Modularization

**Goal:** Refactor the monolithic `ui_system.py` into a modular, dynamic layout system.

**Plans:** 3 plans
- [x] 33-01-PLAN.md — Layout Constants and Y-Cursor Implementation (Wave 1)
- [x] 33-02-PLAN.md — Modular Rendering Functions (Sidebar, Header) (Wave 2)
- [x] 33-03-PLAN.md — Verification & Polish (Wave 3)

**Requirements:** UI-MOD-01, UI-MOD-02, UI-MOD-03, UI-MOD-04

**Success Criteria:**
1. `ui_system.py` contains zero hardcoded positioning literals (magic numbers).
2. UI elements are positioned relative to container boundaries using constants.
3. Sidebar elements stack vertically using a shared Y-cursor logic.
4. Adding a new UI section (e.g., "Needs") requires only a single function call.

---

### Phase 34: Input Handling & Control Scheme

**Goal:** Centralize input and implement context-sensitive interactions.

**Plans:** 3 plans
- [x] 34-01-PLAN.md — InputManager and Command Mapping (Wave 1)
- [x] 34-02-PLAN.md — Context-Sensitive "Bump" Interactions (Wave 2)
- [x] 34-03-PLAN.md — Hotbar Action Selection (1-9) (Wave 2)

**Requirements:** INP-01, INP-02, INP-03, INP-04

**Success Criteria:**
1. `InputManager` translates raw keypresses into high-level commands.
2. Bumping into an enemy triggers an attack without selecting an action first.
3. Bumping into a friendly NPC triggers a "Talk" or "Interact" event.
4. Action hotbar allows immediate selection of spells/abilities via numeric keys.

---

### Phase 35: Stateful Menus & Viewport Expansion

**Goal:** Transition to stateful modal overlays and reclaim screen real estate.

**Plans:** 3 plans
- [x] 35-01-PLAN.md — Window/Modal Base System (INFRASTRUCTURE)
- [x] 35-02-PLAN.md — Inventory and Character Overlays (FEATURES)
- [x] 35-03-PLAN.md — Viewport Resizing & HUD Cleanup (POLISH)

**Requirements:** MENU-01, MENU-02, MENU-03, MENU-04

**Success Criteria:**
1. InventoryScreen and CharacterScreen are modal overlays that pause the game.
2. The HUD is stripped of low-priority info, expanding the main map viewport.
3. Input is correctly captured by the top-most modal in a stack.
4. Modals can be opened and closed without losing game state.

---

### Phase 36: Feedback & Information Hierarchy

**Goal:** Enhance player feedback with FCT and log categorization.

**Plans:** 3 plans
- [x] 36-01-PLAN.md — Floating Combat Text (FCT) System (Wave 1)
- [x] 36-02-PLAN.md — Message Log Categorization & Visuals (Wave 2)
- [x] 36-03-PLAN.md — Examine Mode Tooltips (Wave 3)

**Requirements:** FEED-01, FEED-02, FEED-03, FEED-04

**Success Criteria:**
1. Damage numbers float above entities when they take hits.
2. Message log entries are color-coded based on event type.
3. "Examine" mode provides detailed tooltips for items and entities on the map.
4. Critical alerts (low health, reputation change) have distinct visual emphasis.

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 33 | v1.6 | 3/3 | Done | 2026-02-20 |
| 34 | v1.6 | 3/3 | Done | 2026-02-20 |
| 35 | v1.6 | 3/3 | Done | 2026-02-21 |
| 36 | v1.6 | 3/3 | Done | 2026-02-21 |
