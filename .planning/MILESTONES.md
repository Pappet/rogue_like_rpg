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

