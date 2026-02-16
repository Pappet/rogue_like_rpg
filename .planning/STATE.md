# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.4 Item & Inventory System — Complete

## Current Position

Phase: 26 of 26 (Consumables and Polish)
Plan: 2 of 2 in current phase
Status: Complete
Last activity: 2026-02-16 — Completed Phase 26: Consumables and Polish (Plan 02). Milestone v1.4 Complete.

Progress: [██████████] 100% (Phase 26) / 100% (v1.4)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.4): 12
- Average duration: 21m
- Total execution time: 275m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23 | 2 | 50m | 25m |
| 24 | 3 | 75m | 25m |
| 25 | 5 | 110m | 22m |
| 26 | 2 | 40m | 20m |

**Recent Trend:** Completed v1.4 milestone.

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
- **Equipment Inventory Persistence:** Equipped items remain in the `Inventory.items` list for simple UI listing and persistence; equipment status is tracked via entity ID references in the `Equipment.slots` map. (v1.4 refinement)
- **Equipment Slot Definitions:** Uses `SlotType` enum (HEAD, BODY, MAIN_HAND, OFF_HAND, FEET, ACCESSORY).
- **Equipment Component:** Stores mapping of `SlotType` to entity ID references.
- **Equipment Interaction:** Pressing E/Enter in inventory toggles equipment status via `equipment_service`; equipped items are marked with `(E)` in UI; sidebar displays full loadout and combat stats from `EffectiveStats`. (v1.4 UI refinement)
- **Immediate Effective HP Update in Combat:** CombatSystem manually updates `EffectiveStats.hp` after applying damage to base `Stats.hp`. This prevents stale death checks and ensuring consistency between systems without waiting for the next `EquipmentSystem` process. (v1.4 gap fix)
- **Consumable System:** Uses a `Consumable` component with `effect_type` and `amount`. Managed by `ConsumableService`. Full-health checks prevent wasting items. Immediate `EffectiveStats` update ensures UI consistency.
- **Detailed Physical Descriptions:** Centralized in `ActionSystem.get_detailed_description`, including material and weight. Consistent across Inventory UI and Inspection mode.

### Pending Todos

None.

### Blockers/Concerns

- **NPC inventory freeze/thaw:** No NPC template may include an Inventory component until NPC inventory freeze/thaw ID remapping is implemented (not in v1.4 scope).

## Session Continuity

Last session: 2026-02-16
Stopped at: Completed Phase 26. v1.4 Milestone Complete.
Resume file: .planning/phases/26-consumables-and-polish/26-02-SUMMARY.md
Process Group PGID: 113499
Process Group PGID: 121781
Process Group PGID: 122100