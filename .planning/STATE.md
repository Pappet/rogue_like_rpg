# Project State: Rogue Like RPG

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-17)

**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.
**Current Focus:** v1.5 World Clock & NPC Schedules — Planning

## Current Position

Phase: 29 of 32 (Pathfinding Service)
Plan: 2 of 3 in current phase
Status: In progress
Last activity: 2026-02-19 — Completed AI Navigation Integration (29-02).

Progress: [███████░░░] 66% (Phase 29) / 72% (v1.5)

## Performance Metrics

**Velocity:**
- Total plans completed (v1.5): 8
- Average duration: 25m
- Total execution time: 200m

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 27 | 3 | 75m | 25m |
| 28 | 3 | 75m | 25m |
| 29 | 2 | 50m | 25m |
| 30 | 0 | 0m | 0m |
| 31 | 0 | 0m | 0m |
| 32 | 0 | 0m | 0m |

**Recent Trend:** Completed Pathfinding Service and AI Navigation Integration.

## Quick Tasks Completed

| Task | Description | Date |
|------|-------------|------|
| 29-02 | AI Navigation Integration into AISystem | 2026-02-19 |
| 29-01 | Implement PathfindingService and PathData component | 2026-02-19 |
| smooth-tint-transitions | Interpolate viewport tint for smooth transitions | 2026-02-18 |
| 28-03 | Update VisibilitySystem and run verification | 2026-02-18 |
| 28-02 | Implement viewport tinting in RenderService | 2026-02-18 |
| 28-01 | Define time-of-day settings and update stats pipeline | 2026-02-18 |
| 27-03 | Comprehensive Verification of World Clock | 2026-02-17 |
| 27-02 | Map Travel and UI Header | 2026-02-17 |
| 27-01 | Implement WorldClockService and integrate into TurnSystem | 2026-02-17 |
| fix-action-system-world-attribute | Fix AttributeError in ActionSystem.confirm_action | 2026-02-16 |
| fix-consumable-service-call | Fix AttributeError in ConsumableService call | 2026-02-16 |
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
- **Synchronized WorldClock:** `round_counter` is derived from `total_ticks + 1`. 1 turn = 1 tick. 60 ticks = 1 hour. (v1.5 foundation)
- **Time-consuming map transitions:** Portals can have `travel_ticks` which advance the world clock during transitions. (v1.5 foundation)
- **AI Navigation Fallback:** If A* pathfinding fails or a path is blocked, the AI reverts to a greedy Manhattan step to maintain pressure on the target while waiting for a path to clear. (v1.5)
- **Dynamic Path Invalidation:** NPCs automatically clear and recompute paths if the target moves or if their next step is blocked by an entity. (v1.5)

### Pending Todos

- [ ] Milestone v1.5 Planning (Dungeon Progression / Map Generation)

### Blockers/Concerns

- **NPC inventory freeze/thaw:** No NPC template may include an Inventory component until NPC inventory freeze/thaw ID remapping is implemented (not in v1.4 scope).

## Session Continuity

Last session: 2026-02-17
Stopped at: Completed Phase 27. WorldClock Foundation verified.
Resume file: .planning/phases/27-world-clock-foundation/27-03-SUMMARY.md
