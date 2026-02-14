# Project Roadmap: Rogue Like RPG

## Milestones

- ✅ **v1.0 MVP** — Phases 1-11 (shipped 2026-02-14)
- 🚧 **v1.1 Investigation System** — Phases 12-14 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-11) — SHIPPED 2026-02-14</summary>

| Phase | Name | Plans | Status |
|-------|------|-------|--------|
| 1 | Game Foundation | 1 | ✓ Complete |
| 2 | Core Gameplay Loop | 4 | ✓ Complete |
| 3 | Core Gameplay Mechanics | 5 | ✓ Complete |
| 4 | Combat & Feedback | 4 | ✓ Complete |
| 5 | Nested World Architecture | 3 | ✓ Complete |
| 6 | Advanced Navigation & UI | 2 | ✓ Complete |
| 7 | Layered Rendering & Structure | 1 | ✓ Complete |
| 8 | Procedural Map Features | 2 | ✓ Complete |
| 9 | Data-Driven Core | 2 | ✓ Complete |
| 10 | Entity & Map Templates | 2 | ✓ Complete |
| 11 | Investigation Preparation | 1 | ✓ Complete |

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

---

### 🚧 v1.1 Investigation System (In Progress)

**Milestone Goal:** Player can inspect tiles and entities in their field of view using a free targeting cursor, with dynamic descriptions based on entity state, formatted output in the message log, and distinct visual feedback for investigation mode.

#### Phase 12: Action Wiring

**Goal**: The Investigate action routes through the targeting system so the player can activate, navigate, and cancel a look-mode cursor.
**Depends on**: Phase 11 (Description component exists; TARGETING state and draw_targeting_ui() already in place)
**Requirements**: INV-01, INV-03, INV-04, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Player selects "Investigate" from the action list and a cyan cursor appears on the map at the player position.
  2. Arrow keys move the cursor while the game remains in targeting mode (enemy turns do not fire).
  3. Pressing Escape cancels investigation and returns to normal play with no turn consumed.
  4. The header text reads "Investigating..." when investigation targeting is active (distinct from "Targeting..." for combat).
  5. The investigation cursor is cyan; the combat targeting cursor remains yellow.
**Plans**: 1 plan

Plans:
- [ ] 12-01-PLAN.md — Wire Investigate action through targeting system with cyan cursor, mode-aware header, and free-action confirm

#### Phase 13: Range and Movement Rules

**Goal**: The investigation cursor respects perception-derived range and movement is allowed over explored (shrouded/forgotten) tiles but blocked on unexplored tiles.
**Depends on**: Phase 12
**Requirements**: INV-02, TILE-03
**Success Criteria** (what must be TRUE):
  1. Investigation cursor cannot move beyond a range equal to the player's perception stat.
  2. The cursor can move to SHROUDED (previously seen) tiles as well as VISIBLE tiles.
  3. The cursor cannot move onto UNEXPLORED tiles.
**Plans**: TBD

Plans:
- [ ] 13-01: TBD

#### Phase 14: Inspection Output

**Goal**: Confirming investigation on a tile produces formatted, colored results in the message log covering the tile, all entities at that position, and HP-aware dynamic descriptions.
**Depends on**: Phase 13
**Requirements**: TILE-01, TILE-02, ENT-01, ENT-02, ENT-03, ENT-04, UI-01
**Success Criteria** (what must be TRUE):
  1. Confirming investigation on a VISIBLE tile prints the tile name and base description in the message log with colored formatting.
  2. Confirming investigation on a SHROUDED tile prints only the tile name (no entity information shown).
  3. All entities at the investigated position are listed in the message log (multiple entities are all reported).
  4. An entity below its HP wound threshold shows wounded flavor text (e.g., "looks wounded") rather than the healthy description.
  5. Entities without a Stats component (portals, corpses) produce a description without crashing.
**Plans**: TBD

Plans:
- [ ] 14-01: TBD

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-11 | v1.0 | 27/27 | Complete | 2026-02-14 |
| 12. Action Wiring | v1.1 | 0/1 | Planned | - |
| 13. Range and Movement Rules | v1.1 | 0/TBD | Not started | - |
| 14. Inspection Output | v1.1 | 0/TBD | Not started | - |
