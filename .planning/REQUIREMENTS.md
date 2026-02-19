# Requirements: Rogue Like RPG — v1.5 World Clock & NPC Schedules

**Defined:** 2026-02-17
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat. "Sehr offenes, simulationslastiges Roguelike — tiefgründig und offen, mit Leben."

## v1 Requirements

Requirements for v1.5 milestone. Each maps to roadmap phases.

### World Clock
- **CLK-01**: WorldClock tracks ticks, hours (0-23), days; advances on each player turn
- **CLK-02**: Time-of-day phases (DAWN, DAY, DUSK, NIGHT) derived from hour with configurable boundaries
- **CLK-03**: `clock_tick` event dispatched on each advance with current time state
- **CLK-04**: Map transitions advance clock by configurable travel duration (not free)
- **CLK-05**: Current time and day displayed in header UI

### Day/Night Cycle
- **DN-01**: Global ambient light multiplier derived from time-of-day phase
- **DN-02**: Player perception stat reduced during NIGHT (configurable multiplier, e.g., 0.5x)
- **DN-03**: RenderService applies time-based darkening tint (night is darker, dawn/dusk intermediate)
- **DN-04**: VisibilitySystem uses effective perception (after time-of-day modifier) for FOV radius

### NPC Schedules
- **SCHED-01**: Schedule component holds ordered list of time-ranged activity entries
- **SCHED-02**: Schedule templates loaded from `schedules.json` via data pipeline
- **SCHED-03**: ScheduleSystem checks current time each AI turn and updates NPC target + state
- **SCHED-04**: New AIState values: SLEEP, WORK, PATROL, SOCIALIZE
- **SCHED-05**: NPCs without schedules fall back to existing WANDER behavior (backward compatible)

### Pathfinding
- **PATH-01**: A* pathfinding service computes walkable paths on a single MapContainer layer
- **PATH-02**: PathData component stores precomputed path as coordinate list
- **PATH-03**: AI movement consumes one step from PathData per turn (replaces random wander for scheduled movement)
- **PATH-04**: Path recomputed when destination changes or path is blocked
- **PATH-05**: Pathfinding integrates with existing blocker detection (no walking through entities)

### Sleep Behavior
- **SLEEP-01**: SLEEP state suppresses all detection (no WANDER→CHASE transition)
- **SLEEP-02**: Adjacent combat or player bump wakes sleeping NPC (state → CHASE or ALERT)
- **SLEEP-03**: Sleeping NPCs have visual indicator (dimmed color or 'z' overlay)
- **SLEEP-04**: NPCs navigate to home position before entering SLEEP state

### Data Extension
- **DATA-01**: `schedules.json` defines reusable schedule templates with time ranges and activities
- **DATA-02**: Entity templates reference schedule by ID (`schedule_id` field)
- **DATA-03**: At least 3 NPC archetypes with distinct schedules (Villager, Guard, Shopkeeper)
- **DATA-04**: Village scenario populated with scheduled friendly NPCs

## Out of Scope

| Feature | Reason |
|---------|--------|
| Cross-map NPC pathfinding | Requires portal-aware graph; too complex for v1.5 |
| NPC needs (hunger, thirst) | Depends on clock but is a separate milestone (v1.7) |
| Weather system | Depends on clock but is a separate milestone |
| Torch/lantern items | Light sources exist in components but torch item logic deferred |
| NPC dialogue content | v1.6 milestone; TALK state remains placeholder |
| Seasonal changes | Clock tracks season but no gameplay effect in v1.5 |
| Save/Load clock state | Persistence milestone not yet planned |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| CLK-01, CLK-02, CLK-03, CLK-04, CLK-05 | Phase 27 | Pending |
| DN-01, DN-02, DN-03, DN-04 | Phase 28 | Pending |
| PATH-01, PATH-02, PATH-03, PATH-04, PATH-05 | Phase 29 | Pending |
| SCHED-02, DATA-01 | Phase 30 | Pending |
| SCHED-01, SCHED-03, SCHED-04, SCHED-05 | Phase 31 | Pending |
| SLEEP-01, SLEEP-02, SLEEP-03, SLEEP-04, DATA-02, DATA-03, DATA-04 | Phase 32 | Pending |

---
*Requirements defined: 2026-02-17*
