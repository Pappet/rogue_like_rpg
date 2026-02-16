# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.4 Item & Inventory System — Phase 24: Pickup, Inventory Screen, and Loot Drops

## Current Position

Phase: 24 of 26 (Pickup, Inventory Screen, and Loot Drops)
Plan: 1 of 1 in current phase (Phase 24-01 Complete)
Status: In progress
Last activity: 2026-02-16 — Completed Phase 24-01 (Inventory Screen and Navigation)

Progress: [████░░░░░░] 40% (v1.4)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.4): 2
- Average duration: 25m
- Total execution time: 50m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23 | 2 | 50m | 25m |

**Recent Trend:** Completed Phase 23.

*Updated after each plan completion*

## Accumulated Context

### Decisions

- **Items as entities with position XOR parent:** Position component removed on pickup; carried items have no Position, preventing phantom rendering with zero changes to RenderSystem or MovementSystem. (v1.4 architectural constraint)
- **EffectiveStats pattern (never delta-mutate Stats):** EquipmentSystem computes EffectiveStats each frame from base Stats + equipped bonuses; base Stats fields are never modified by equip/unequip. Eliminates irreversible state bugs.
- **get_entity_closure() wired at Phase 23:** Freeze/thaw inventory corruption is binary — fix it at foundation or audit the whole milestone. Player + Inventory.items + equipped item IDs passed to MapContainer.freeze().
- **LootSystem as separate event handler:** Registered alongside DeathSystem on "entity_died"; keeps loot spawning decoupled from corpse transformation and independently testable.
- **Stats component base fields:** Explicitly named `base_hp`, `base_power`, etc., added to `Stats` component to support the Effective Stats pattern.
- **ItemFactory Implementation:** `ItemFactory` creates items from templates. Items on ground have a `Position`, while carried items (in an inventory) do not.

### Pending Todos

None.

### Blockers/Concerns

- **NPC inventory freeze/thaw:** No NPC template may include an Inventory component until NPC inventory freeze/thaw ID remapping is implemented (not in v1.4 scope).

## Session Continuity

Last session: 2026-02-15
Stopped at: Completed Phase 23.
Resume file: .planning/phases/24-pickup-inventory-screen-loot-drops/24-01-PLAN.md
Process Group PGID: 113499
