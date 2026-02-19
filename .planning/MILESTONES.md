# Milestones

## v1.0 MVP (Shipped: 2026-02-14)

**Phases:** 11 | **Plans:** 27 | **Commits:** 138 | **Python LOC:** 3,892
**Timeline:** 7 days (2026-02-07 → 2026-02-14)

**Key accomplishments:**
- ECS-based game engine with PyGame rendering, tile-based maps, turn-based movement, and party system
- Combat system with bump attacks, damage calculation, death/corpse mechanics, and message log
- Nested world architecture with portals, multi-container maps, and transition logic
- Advanced navigation with time-based map memory aging and world map overview UI
- Procedural generation with building generators, terrain variety, and layered depth rendering
- Data-driven architecture with JSON registries for tiles, entities, and map prefabs
- Dynamic entity descriptions with context-aware text based on HP state

---


## v1.1 Investigation System (Shipped: 2026-02-14)

**Phases:** 3 (12-14) | **Plans:** 3 | **Requirements:** 14/14 satisfied
**Timeline:** 1 day (2026-02-14)
**Git range:** a6469a5 → 06cf3cd

**Key accomplishments:**
- Wired Investigate action through targeting system with free-action behavior and cyan cursor
- Implemented perception-stat-derived range limiting for investigation targeting
- Expanded cursor movement to explored (SHROUDED/FORGOTTEN) tiles while blocking UNEXPLORED
- Built formatted inspection output with tile info, entity listing, and HP-aware descriptions
- Stats-less entities (portals, corpses) handled gracefully without crash
- 28 automated tests covering all 14 requirements across 3 phases

---


## v1.2 AI Infrastructure (Shipped: 2026-02-15)

**Phases:** 4 (15-18) | **Plans:** 4 | **Tasks:** 8 | **Requirements:** 20/20 satisfied
**Timeline:** 2 days (2026-02-14 → 2026-02-15)
**Git range:** 3d9f98c → fb42bae | **Files changed:** 27 (+3,750/-32) | **Python LOC:** 5,959

**Key accomplishments:**
- AI component pipeline — AIState/Alignment enums, AIBehaviorState/ChaseData wired through full JSON-to-factory-to-death pipeline
- AISystem processor owns enemy turns with layer filtering, corpse exclusion, and explicit-call pattern
- Wander behavior — NPCs move randomly each turn with walkability, blocker detection, and per-turn tile reservation
- Chase behavior — hostile NPCs detect player via FOV, pursue with greedy Manhattan steps, revert after losing sight
- Safety guarantees — coordinates-only state storage (freeze/thaw safe), wrong-layer exclusion, dead entity skip
- Post-ship fix: Player entity missing Blocker() component (NPCs could stack on player tile)

---


## v1.3 Debug Overlay System (Shipped: 2026-02-15)

**Phases:** 4 (19-22) | **Plans:** 6 | **Requirements:** 13/13 satisfied
**Timeline:** 1 day (2026-02-15)

**Key accomplishments:**
- Decoupled `DebugRenderSystem` with independent overlay surface and zero performance impact when disabled
- Multi-layer debug visualization — FOV highlights, AI state labels, and chase targets
- Granular diagnostic controls — independent toggles for FOV, labels, chase vectors, and NPC FOV cones
- Advanced AI visualization — NPC sight-loss counters, chase direction vectors, and hostile-distinguishing FOV tints
- Bulletproof integration — persistent debug state across map transitions, layer-aware rendering, and map-syncing
- Alignment with AI logic — debug visibility uses identical `#` wall fallback as pathfinding/detection
- Automated verification — passing regression tests for the expanded debug pipeline

---


## v1.4 Item & Inventory System (Shipped: 2026-02-16)

**Phases:** 4 (23-26) | **Plans:** 13 | **Requirements:** 22/22 satisfied
**Timeline:** 1 day (2026-02-16)

**Key accomplishments:**
- **Item Entity Pipeline:** Items are first-class ECS entities with identity continuity across world, inventory, and equipment states.
- **Physical Properties:** Weight and material data-driven through JSON, enabling simulation-first mechanics like capacity limits.
- **Inventory Management:** Full UI for navigating, picking up, dropping, equipping, and using items from a weight-bounded inventory.
- **Equipment System:** Component-based slot mapping with dynamic `EffectiveStats` calculation, ensuring base stats are never permanently mutated.
- **Consumables:** Data-driven healing potions with safety checks and immediate stat feedback.
- **Detailed Inspection:** Physical item properties (material, weight) integrated into both inventory descriptions and world inspection modes.
- **Safety & Persistence:** Item closure tracking during map transitions prevents entity loss or duplication.

---

## v1.5 World Clock & NPC Schedules (In Progress)

**Goal:** Give the world a persistent time system that drives day/night cycles, NPC daily routines, and time-aware gameplay.

**Target features:**
- World Clock (ticks, hours, days, seasons)
- Day/Night Visual Cycle (ambient light, perception modifiers)
- NPC Schedule System (SLEEP, WORK, PATROL, SOCIALIZE)
- A* Pathfinding Service
- NPC Sleep Behavior
- Data-driven schedule templates

