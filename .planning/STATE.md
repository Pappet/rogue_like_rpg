# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.4 Item & Inventory System — Phase 24: Pickup, Inventory Screen, and Loot Drops

## Current Position

Phase: 24 of 26 (Pickup, Inventory Screen, and Loot Drops)
Plan: 3 of 3 in current phase (Phase 24 Complete)
Status: Complete
Last activity: 2026-02-16 — Completed Phase 24-03 (Loot Drops)

Progress: [████████░░] 80% (v1.4)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.4): 5
- Average duration: 25m
- Total execution time: 125m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23 | 2 | 50m | 25m |
| 24 | 3 | 75m | 25m |

**Recent Trend:** Completed Phase 24 and fixed MapContainer attribute error.

## Quick Tasks Completed

| Task | Description | Date |
|------|-------------|------|
| fix-map-container-attribute-error | Implement `is_walkable` in `MapContainer` | 2026-02-16 |

*Updated after each plan completion*

## Accumulated Context

### Decisions

- **Items as entities with position XOR parent:** Position component removed on pickup; carried items have no Position, preventing phantom rendering with zero changes to RenderSystem or MovementSystem. (v1.4 architectural constraint)
- **EffectiveStats pattern (never delta-mutate Stats):** EquipmentSystem computes EffectiveStats each frame from base Stats + equipped bonuses; base Stats fields are never modified by equip/unequip. Eliminates irreversible state bugs.
- **get_entity_closure() wired at Phase 23:** Freeze/thaw inventory corruption is binary — fix it at foundation or audit the whole milestone. Player + Inventory.items + equipped item IDs passed to MapContainer.freeze().
- **LootSystem as separate event handler:** Registered alongside DeathSystem on "entity_died"; keeps loot spawning decoupled from corpse transformation and independently testable.
- **Stats component base fields:** Explicitly named `base_hp`, `base_power`, etc., added to `Stats` component to support the Effective Stats pattern.
- **ItemFactory Implementation:** `ItemFactory` creates items from templates. Items on ground have a `Position`, while carried items (in an inventory) do not.
- **Spatial Loot Scattering:** If an entity's death tile is blocked, loot drops search 8 neighbors for a walkable tile, preventing lost items in walls. (v1.4 loot policy)
- **DeathSystem as Loot Spawner:** LootTable processing is integrated directly into DeathSystem's `on_entity_died` handler, leveraging the existing map-aware system for spatial checks.

### Pending Todos

None.

### Blockers/Concerns

- **NPC inventory freeze/thaw:** No NPC template may include an Inventory component until NPC inventory freeze/thaw ID remapping is implemented (not in v1.4 scope).

## Session Continuity

Last session: 2026-02-15
Stopped at: Completed Phase 23.
Resume file: .planning/phases/24-pickup-inventory-screen-loot-drops/24-01-PLAN.md
Process Group PGID: 113499
