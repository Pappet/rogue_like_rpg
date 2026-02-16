# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-15)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.4 Item & Inventory System — Phase 25: Equipment Slots and Combat Integration

## Current Position

Phase: 25 of 26 (Equipment Slots and Combat Integration)
Plan: 3 of 4 in current phase
Status: In Progress
Last activity: 2026-02-16 — Completed Phase 25 Plan 03 (Equipment Logic and UI).

Progress: [██████████] 95% (v1.4)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.4): 8
- Average duration: 23m
- Total execution time: 183m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 23 | 2 | 50m | 25m |
| 24 | 3 | 75m | 25m |
| 25 | 3 | 58m | 19m |

**Recent Trend:** Completed Phase 25 Plan 03.

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

### Pending Todos

None.

### Blockers/Concerns

- **NPC inventory freeze/thaw:** No NPC template may include an Inventory component until NPC inventory freeze/thaw ID remapping is implemented (not in v1.4 scope).

## Session Continuity

Last session: 2026-02-16
Stopped at: Completed Phase 24 and refined Phase 25 plans.
Resume file: .planning/phases/25-equipment-slots-combat-integration/25-01-PLAN.md
Process Group PGID: 113499
