# Project Roadmap: Rogue Like RPG

## Milestones

- ✅ **v1.0 MVP** — Phases 1-11 (shipped 2026-02-14)
- ✅ **v1.1 Investigation System** — Phases 12-14 (shipped 2026-02-14)
- ✅ **v1.2 AI Infrastructure** — Phases 15-18 (shipped 2026-02-15)
- ✅ **v1.3 Debug Overlay System** — Phases 19-22 (shipped 2026-02-15)

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

<details>
<summary>✅ v1.1 Investigation System (Phases 12-14) — SHIPPED 2026-02-14</summary>

- [x] Phase 12: Action Wiring (1/1 plans) — completed 2026-02-14
- [x] Phase 13: Range and Movement Rules (1/1 plans) — completed 2026-02-14
- [x] Phase 14: Inspection Output (1/1 plans) — completed 2026-02-14

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 AI Infrastructure (Phases 15-18) — SHIPPED 2026-02-15</summary>

- [x] Phase 15: AI Component Foundation (1/1 plans) — completed 2026-02-14
- [x] Phase 16: AISystem Skeleton and Turn Wiring (1/1 plans) — completed 2026-02-14
- [x] Phase 17: Wander Behavior (1/1 plans) — completed 2026-02-15
- [x] Phase 18: Chase Behavior and State Transitions (1/1 plans) — completed 2026-02-15

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

---

## v1.3 Debug Overlay System

**Goal:** Deliver an extensible debug overlay for visualizing internal game state — FOV tiles, AI state labels, chase markers, and direction vectors — as a dedicated `DebugRenderSystem` that sits after the main render pass and has zero performance impact when disabled.

**Coverage:** 13/13 v1.3 requirements mapped (DBG-01 to DBG-05, OVL-01 to OVL-04, EXT-01 to EXT-04)

---

### Phase 19: Debug Infrastructure

**Goal:** The debug toggle and system skeleton exist, are wired into the render pipeline, and the game runs identically with debug off.

**Dependencies:** Phase 18 (game loop and render pipeline must be stable before inserting a new draw stage)

**Requirements:** DBG-01, DBG-02, DBG-03, DBG-04, DBG-05

**Plans:** 1

**Plans:**
- [x] 19-01-PLAN.md — Implement DebugRenderSystem and toggle hotkey

**Success Criteria:**

1. Pressing the debug hotkey (F1 or F3) flips a visible flag and does not crash the game or alter gameplay.
2. The toggle state is preserved when transitioning between Game state and WorldMapState (stored in `persist["debug_enabled"]`).
3. Frame time with debug disabled is identical to the pre-overlay baseline — no allocations happen in the disabled code path.
4. `DebugRenderSystem` is instantiated in `Game.startup()`, called inside the `surface.set_clip(viewport_rect)` block after `render_system.process()`, and is not registered with `esper.add_processor()`.
5. All debug draw calls target a pre-allocated `pygame.SRCALPHA` overlay surface created once in `__init__`; no per-frame surface allocation occurs.

---

### Phase 20: Core Overlays

**Goal:** With debug enabled, a developer can see player FOV extent, NPC AI state, and NPC chase targets in a single glance at the game screen.

**Dependencies:** Phase 19 (infrastructure and wiring must exist before any overlay can draw)

**Requirements:** OVL-01, OVL-02, OVL-03, OVL-04

**Plans:** 1

**Plans:**
- [x] 20-01-PLAN.md — Implement Core Debug Overlays

**Success Criteria:**

1. With debug on, every tile where the player has current line-of-sight shows a distinct green tint; tiles outside FOV are unaffected.
2. With debug on, every NPC with an `AIBehaviorState` component shows a short label (W, C, I, or T) above its sprite.
3. With debug on, every NPC in CHASE state shows an orange rectangle at its `ChaseData.last_known_x/y` coordinates.
4. All overlays are clipped to the viewport region — no debug graphics appear over the header, sidebar, or message log.
5. FOV tile tints render before entity sprites (tile-layer pass); AI labels and chase markers render after entity sprites (entity-layer pass) — no z-order bleed between the two.

---

### Phase 21: Extended Overlays

**Goal:** A developer diagnosing a chase or detection bug can see the direction of NPC pursuit, how many turns remain until a chasing NPC gives up, the FOV cone each NPC is actively computing, and can silence any individual overlay layer independently.

**Dependencies:** Phase 20 (core overlays must be validated in use before adding signal density)

**Requirements:** EXT-01, EXT-02, EXT-03, EXT-04

**Plans:** 3

**Plans:**
- [x] 21-01-PLAN.md — Implement granular debug flags and input handling
- [x] 21-02-PLAN.md — Implement chase vectors and sight-loss counters
- [x] 21-03-PLAN.md — Implement NPC field-of-view visualization

**Success Criteria:**

1. With debug on, every CHASE-state NPC shows an arrow line from its current position to its last-known player position.
2. The AI state label for a chasing NPC includes the turns-without-sight counter (e.g., `C(2)`), updating each enemy turn.
3. With debug on, every NPC's computed FOV tiles receive a color tint distinguishing hostile from friendly NPCs; the tint reflects the actual shadowcast result from `VisibilityService`.
4. Each overlay layer (FOV highlight, AI labels, chase markers, chase vectors, NPC FOV cones) can be toggled on or off independently without affecting other layers.
5. Disabling all individual overlays via per-layer toggles produces a screen identical to having debug mode off.

---

### Phase 22: Debug System Refinement

**Goal:** Fix stale data after map transitions, align transparency logic with AI systems, and repair outdated verification tests.

**Dependencies:** Phase 21 (all overlays must exist before they can be refined)

**Requirements:** DBG-03, EXT-03

**Gap Closure:** Closes integration and logic gaps from v1.3 audit.

**Plans:** 1

**Plans:**
- [x] 22-01-PLAN.md — Fix map synchronization and transparency logic — completed 2026-02-15

**Success Criteria:**

1. Entering a new map (e.g., a village) immediately updates the debug overlay with the new map's visibility and AI state.
2. NPC FOV visualization in debug mode exactly matches the actual visibility used by the AI (tested against `#` wall fallback).
3. `tests/verify_phase_20.py` passes with the updated `DebugRenderSystem.process` signature.
4. Debug overlay remains functional and accurate across multiple map transitions in a single session.

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-11 | v1.0 | 27/27 | Complete | 2026-02-14 |
| 12. Action Wiring | v1.1 | 1/1 | Complete | 2026-02-14 |
| 13. Range and Movement Rules | v1.1 | 1/1 | Complete | 2026-02-14 |
| 14. Inspection Output | v1.1 | 1/1 | Complete | 2026-02-14 |
| 15. AI Component Foundation | v1.2 | 1/1 | Complete | 2026-02-14 |
| 16. AISystem Skeleton and Turn Wiring | v1.2 | 1/1 | Complete | 2026-02-14 |
| 17. Wander Behavior | v1.2 | 1/1 | Complete | 2026-02-15 |
| 18. Chase Behavior and State Transitions | v1.2 | 1/1 | Complete | 2026-02-15 |
| 19. Debug Infrastructure | v1.3 | 1/1 | Complete | 2026-02-15 |
| 20. Core Overlays | v1.3 | 1/1 | Complete | 2026-02-15 |
| 21. Extended Overlays | v1.3 | 3/3 | Complete | 2026-02-15 |
| 22. Debug System Refinement | v1.3 | 1/1 | Complete | 2026-02-15 |