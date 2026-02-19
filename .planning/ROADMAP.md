# Project Roadmap: Rogue Like RPG

## Milestones

- ✅ **v1.0 MVP** — Phases 1-11 (shipped 2026-02-14)
- ✅ **v1.1 Investigation System** — Phases 12-14 (shipped 2026-02-14)
- ✅ **v1.2 AI Infrastructure** — Phases 15-18 (shipped 2026-02-15)
- ✅ **v1.3 Debug Overlay System** — Phases 19-22 (shipped 2026-02-15)
- ✅ **v1.4 Item & Inventory System** — Phases 23-26 (shipped 2026-02-16)
- 🏗️ **v1.5 World Clock & NPC Schedules** — Phases 27-32 (In Progress)

## Phases

### ✅ v1.0 - v1.4 (Phases 1-26)
See archived roadmaps in `.planning/milestones/`.

---

## 🏗️ v1.5 World Clock & NPC Schedules

**Milestone Goal:** Give the world a persistent time system that drives day/night cycles, NPC daily routines, and time-aware gameplay.

**Coverage:** CLK-01 to CLK-05, DN-01 to DN-04, SCHED-01 to SCHED-05, PATH-01 to PATH-05, SLEEP-01 to SLEEP-04, DATA-01 to DATA-04.

---

### Phase 27: WorldClock Foundation

**Goal:** Implement the core timekeeping service and integrate it into the turn loop.

**Plans:** 3 plans
- [x] 27-01-PLAN.md — WorldClock Service and Turn Integration
- [x] 27-02-PLAN.md — Map Travel and UI Header
- [x] 27-03-PLAN.md — Verification

**Requirements:** CLK-01, CLK-02, CLK-03, CLK-04, CLK-05

**Success Criteria:**
1. `WorldClock` service exists and advances by N ticks on each `end_player_turn` call.
2. Time-of-day phases (DAWN, DAY, DUSK, NIGHT) are correctly derived from current hour.
3. `clock_tick` event is dispatched with full time state.
4. Map transitions advance the clock by travel duration.
5. Header UI displays "Day 1 - 12:00 (DAY)".

---

### Phase 28: Day/Night Visual Cycle

**Goal:** Translate world time into visual atmosphere and gameplay perception limits.

**Plans:** 3 plans
- [x] 28-01-PLAN.md — Configuration and Environment Logic
- [x] 28-02-PLAN.md — Visual Atmosphere Implementation
- [x] 28-03-PLAN.md — Gameplay Impact and Verification

**Requirements:** DN-01, DN-02, DN-03, DN-04

**Success Criteria:**
1. `RenderService` applies a global color tint based on the current time phase (darker at night).
2. Player perception stat is dynamically halved during the NIGHT phase via `EffectiveStats`.
3. FOV radius in `VisibilitySystem` shrinks/expands based on current time-of-day.
4. Ambient light levels transition smoothly through DAWN and DUSK.

---

### Phase 29: Pathfinding Service

**Goal:** Provide NPCs with the ability to navigate purposefully to destinations.

**Plans:** 3 plans
- [x] 29-01-PLAN.md — Infrastructure & Component
- [x] 29-02-PLAN.md — AI Integration
- [x] 29-03-PLAN.md — Verification

**Requirements:** PATH-01, PATH-02, PATH-03, PATH-04, PATH-05

**Success Criteria:**
1. A* pathfinding service returns a list of coordinates between two points on a map.
2. `PathData` component stores precomputed paths.
3. NPCs follow `PathData` step-by-step during their AI turn.
4. Paths are invalidated and recomputed if the destination moves or the route is blocked.
5. Pathfinding respects tile walkability and entity blockers.

---

### Phase 30: Schedule Data Pipeline

**Goal:** Load NPC routines from external data files.

**Plans:** 3 plans
- [ ] 30-01-PLAN.md — Schedule Registry and Components
- [ ] 30-02-PLAN.md — Data Loading and Pipeline
- [ ] 30-03-PLAN.md — Verification

**Requirements:** SCHED-02, DATA-01

**Success Criteria:**
1. `assets/data/schedules.json` defines reusable schedule templates.
2. `ResourceLoader` and `Registry` expanded to handle schedule data.
3. Schedule templates can be looked up by ID.
4. NPCs can be assigned a `schedule_id` in `entities.json`.

---

### Phase 31: ScheduleSystem & Activity States

**Goal:** Wire NPC AI to follow their assigned schedules.

**Requirements:** SCHED-01, SCHED-03, SCHED-04, SCHED-05

**Success Criteria:**
1. `ScheduleSystem` processor updates NPC target coordinates based on current world time.
2. NPCs transition between states (WORK, PATROL, SOCIALIZE, etc.) according to schedule.
3. NPCs without schedules maintain their existing WANDER behavior.
4. ScheduleSystem triggers pathfinding when the current activity's target location changes.

---

### Phase 32: Sleep Behavior & Village Population

**Goal:** Complete the simulation with sleep mechanics and a populated Village scenario.

**Requirements:** SLEEP-01, SLEEP-02, SLEEP-03, SLEEP-04, DATA-02, DATA-03, DATA-04

**Success Criteria:**
1. NPCs in SLEEP state do not move or detect the player.
2. Sleeping NPCs display a "z" overlay or dimmed sprite.
3. Player bumping or adjacent combat wakes sleeping NPCs.
4. NPCs navigate to their `home_x`/`home_y` before sleeping.
5. Village scenario features Villagers, Guards, and Shopkeepers following full daily routines.

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 27 | v1.5 | 3/3 | Done | 2026-02-17 |
| 28 | v1.5 | 3/3 | Done | 2026-02-18 |
| 29 | v1.5 | 3/3 | Done | 2026-02-19 |
| 30 | v1.5 | 0/3 | Pending | - |
| 31 | v1.5 | 0/? | Pending | - |
| 32 | v1.5 | 0/? | Pending | - |
