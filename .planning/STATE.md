# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.4 Item & Inventory System — Phase 23: Item Entity Foundation

## Current Position

Phase: 23 of 26 (Item Entity Foundation)
Plan: 0 of TBD in current phase
Status: Ready to plan
Last activity: 2026-02-15 — Roadmap created for v1.4 (4 phases, 22 requirements mapped)

Progress: [░░░░░░░░░░] 0% (v1.4)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.4): 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| — | — | — | — |

**Recent Trend:** Not enough data

*Updated after each plan completion*

## Accumulated Context

### Decisions

- **Items as entities with position XOR parent:** Position component removed on pickup; carried items have no Position, preventing phantom rendering with zero changes to RenderSystem or MovementSystem. (v1.4 architectural constraint)
- **EffectiveStats pattern (never delta-mutate Stats):** EquipmentSystem computes EffectiveStats each frame from base Stats + equipped bonuses; base Stats fields are never modified by equip/unequip. Eliminates irreversible state bugs.
- **get_entity_closure() wired at Phase 23:** Freeze/thaw inventory corruption is binary — fix it at foundation or audit the whole milestone. Player + Inventory.items + equipped item IDs passed to MapContainer.freeze().
- **LootSystem as separate event handler:** Registered alongside DeathSystem on "entity_died"; keeps loot spawning decoupled from corpse transformation and independently testable.

### Pending Todos

None.

### Blockers/Concerns

- **Stats base field placement:** Research recommends explicit `base_power`/`base_defense` fields on Stats vs. reading existing `stats.power` as the base in EffectiveStats. Must be decided explicitly in Phase 23 plan and documented in PROJECT.md Key Decisions.
- **NPC inventory freeze/thaw:** No NPC template may include an Inventory component until NPC inventory freeze/thaw ID remapping is implemented (not in v1.4 scope).

## Session Continuity

Last session: 2026-02-15
Stopped at: Roadmap written for v1.4. Ready to plan Phase 23.
Resume file: None
