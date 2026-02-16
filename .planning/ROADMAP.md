# Project Roadmap: Rogue Like RPG

## Milestones

- ✅ **v1.0 MVP** — Phases 1-11 (shipped 2026-02-14)
- ✅ **v1.1 Investigation System** — Phases 12-14 (shipped 2026-02-14)
- ✅ **v1.2 AI Infrastructure** — Phases 15-18 (shipped 2026-02-15)
- ✅ **v1.3 Debug Overlay System** — Phases 19-22 (shipped 2026-02-15)
- 🚧 **v1.4 Item & Inventory System** — Phases 23-26 (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1-11) — SHIPPED 2026-02-14</summary>

| Phase | Name | Plans | Status |
|-------|------|-------|--------|
| 1 | Game Foundation | 1 | ✓ Complete |
| 2 | Core Gameplay Loop | 4 | ✓ Complete |
| 3 | Core Gameplay Mechanics | 5 | ✓ Complete |
| 4 | Combat & Feedback | 4 | ✓ Complete |
| 5 | Nested World Architecture | 3 | ✓ Complete |
| 6 | Advanced Navigation & UI | 2 | ✓ Complete |
| 7 | Layered Rendering & Structure | 1 | ✓ Complete |
| 8 | Procedural Map Features | 2 | ✓ Complete |
| 9 | Data-Driven Core | 2 | ✓ Complete |
| 10 | Entity & Map Templates | 2 | ✓ Complete |
| 11 | Investigation Preparation | 1 | ✓ Complete |

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v1.1 Investigation System (Phases 12-14) — SHIPPED 2026-02-14</summary>

- [x] Phase 12: Action Wiring (1/1 plans) — completed 2026-02-14
- [x] Phase 13: Range and Movement Rules (1/1 plans) — completed 2026-02-14
- [x] Phase 14: Inspection Output (1/1 plans) — completed 2026-02-14

Full details: `.planning/milestones/v1.1-ROADMAP.md`

</details>

<details>
<summary>✅ v1.2 AI Infrastructure (Phases 15-18) — SHIPPED 2026-02-15</summary>

- [x] Phase 15: AI Component Foundation (1/1 plans) — completed 2026-02-14
- [x] Phase 16: AISystem Skeleton and Turn Wiring (1/1 plans) — completed 2026-02-14
- [x] Phase 17: Wander Behavior (1/1 plans) — completed 2026-02-15
- [x] Phase 18: Chase Behavior and State Transitions (1/1 plans) — completed 2026-02-15

Full details: `.planning/milestones/v1.2-ROADMAP.md`

</details>

<details>
<summary>✅ v1.3 Debug Overlay System (Phases 19-22) — SHIPPED 2026-02-15</summary>

- [x] Phase 19: Debug Infrastructure (1/1 plans) — completed 2026-02-15
- [x] Phase 20: Core Overlays (1/1 plans) — completed 2026-02-15
- [x] Phase 21: Extended Overlays (3/3 plans) — completed 2026-02-15
- [x] Phase 22: Debug System Refinement (1/1 plans) — completed 2026-02-15

</details>

---

## 🚧 v1.4 Item & Inventory System (In Progress)

**Milestone Goal:** Simulation-first item system where items are full ECS entities with physical properties, a weight-based inventory, equipment slots with dynamic stat modification, consumable items, contextual loot drops, and a full inventory management UI.

**Coverage:** 22/22 v1.4 requirements mapped (ITEM-01 to ITEM-05, INV-01 to INV-06, EQUIP-01 to EQUIP-06, CONS-01 to CONS-05)

---

### Phase 23: Item Entity Foundation

**Goal:** Items exist as first-class ECS entities in the world and survive map transitions intact.

**Dependencies:** Phase 22 (stable ECS and render pipeline)

**Requirements:** ITEM-01, ITEM-02, ITEM-03, ITEM-04, ITEM-05, INV-06

**Plans:** 2 plans

**Plans:**
- [x] 23-01-PLAN.md — ECS Components and Data Loading
- [x] 23-02-PLAN.md — Item Factory and Map Persistence

**Success Criteria:**

1. An item placed on the ground via `ItemFactory.create_on_ground()` renders on the map at its tile position using the existing `RenderSystem` — no changes to the render pipeline required.
2. Item templates defined in `assets/data/items.json` are loaded through the `ItemRegistry`/`ItemFactory` pipeline; a missing or malformed template raises a clear error at startup, not silently at runtime.
3. Each item entity carries a `Portable` component with a `weight` weight field (kg) and an `ItemMaterial` component with a material type (wood, metal, glass, etc.).
4. Picking up an item and crossing a portal into a new map and back returns the carried item with its entity ID and all components intact — no silent destruction or orphaned references.
5. A `get_entity_closure(player_entity)` helper returns the player plus all items in `Inventory.items` plus equipped item IDs; `transition_map()` passes this full list to `MapContainer.freeze()`.

---

### Phase 24: Pickup, Inventory Screen, and Loot Drops

**Goal:** The player can acquire items from the world, see what they are carrying, drop them, and monsters produce contextual loot when they die.

**Dependencies:** Phase 23 (item entities must exist before pickup or loot logic can run)

**Requirements:** INV-01, INV-02, INV-03, INV-04, INV-05, CONS-03, CONS-04

**Plans:** 3 plans

**Plans:**
- [x] 24-01-PLAN.md — Inventory Screen and Navigation
- [x] 24-02-PLAN.md — Pickup and Drop Logic
- [x] 24-03-PLAN.md — Loot Drops

**Success Criteria:**

1. Pressing G picks up an item at the player's current position, removes its `Position` component, appends its entity ID to `Inventory.items`, and logs "You pick up the [item name]." in the message log.
2. Attempting to pick up an item that would exceed the player's weight capacity is rejected with a log message ("Too heavy to carry.") and the item remains on the ground.
3. Pressing I opens a modal inventory screen (`GameStates.INVENTORY`) showing a list of carried item names; arrow keys navigate the list; Escape closes it without consuming a turn.
4. Pressing D from the inventory screen drops the selected item at the player's current tile position, restoring its `Position` component and removing it from `Inventory.items`.
5. When a monster with a loot table dies, at least one contextually appropriate item (e.g., a wolf drops a pelt, not gold) spawns on or adjacent to the death tile — if the death tile is occupied, the item scatters to a walkable neighbor.

---

### Phase 25: Equipment Slots and Combat Integration

**Goal:** The player can equip items to body slots, see their loadout, and equipped gear meaningfully changes combat outcomes.

**Dependencies:** Phase 24 (equip actions are initiated from the inventory screen; items must already be pickable)

**Requirements:** EQUIP-01, EQUIP-02, EQUIP-03, EQUIP-04, EQUIP-05, EQUIP-06

**Plans:** 4 plans

**Plans:**
- [x] 25-01-PLAN.md — Equipment Infrastructure
- [ ] 25-02-PLAN.md — Equipment System and Integration
- [ ] 25-03-PLAN.md — Equipment Logic and UI
- [ ] 25-04-PLAN.md — Combat Integration

**Success Criteria:**

1. From the inventory screen, pressing E (or Enter) on an equippable item toggles its equipment status in the matching slot; items remain in the inventory list and are marked with (E) when equipped.
2. The sidebar UI displays the player's current equipment loadout (head, body, main_hand, off_hand, feet, accessory) and effective combat stats (Power, Defense).
3. `EquipmentSystem` computes an `EffectiveStats` component each frame from base `Stats` plus the sum of all equipped item bonuses; base `Stats` values are never mutated by equip or unequip actions.
4. `CombatSystem` uses `EffectiveStats` for all damage and defense calculations; equipping a sword increases attack output and unequipping it returns damage to the base value.
5. `ActionSystem` and UI bars (HP/MP) correctly handle increases to maximum HP/MP from equipment bonuses using `EffectiveStats`.

---

### Phase 26: Consumables and Polish

**Goal:** The player can use consumable items with immediate, observable effects, and items communicate their physical nature through descriptions.

**Dependencies:** Phase 25 (use action is initiated from the inventory screen; full item pipeline must be complete)

**Requirements:** CONS-01, CONS-02, CONS-05

**Plans:** TBD

**Plans:**
- [ ] 26-01-PLAN.md — TBD

**Success Criteria:**

1. Pressing U on a consumable item in the inventory screen triggers its effect immediately: a health potion restores HP (capped at max), logs "You drink the health potion. (+N HP)", and the item entity is deleted — it no longer appears in inventory.
2. Drinking a health potion when already at full HP logs a message ("You are already at full health.") and does not delete the item.
3. Investigating a material-bearing item (e.g., a wooden club) or reading its inventory description includes the material type in the output (e.g., "A sturdy club made of wood.").

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-11 | v1.0 | 27/27 | Complete | 2026-02-14 |
| 12. Action Wiring | v1.1 | 1/1 | Complete | 2026-02-14 |
| 13. Range and Movement Rules | v1.1 | 1/1 | Complete | 2026-02-14 |
| 14. Inspection Output | v1.1 | 1/1 | Complete | 2026-02-14 |
| 15. AI Component Foundation | v1.2 | 1/1 | Complete | 2026-02-14 |
| 16. AISystem Skeleton and Turn Wiring | v1.2 | 1/1 | Complete | 2026-02-14 |
| 17. Wander Behavior | v1.2 | 1/1 | Complete | 2026-02-15 |
| 18. Chase Behavior and State Transitions | v1.2 | 1/1 | Complete | 2026-02-15 |
| 19. Debug Infrastructure | v1.3 | 1/1 | Complete | 2026-02-15 |
| 20. Core Overlays | v1.3 | 1/1 | Complete | 2026-02-15 |
| 21. Extended Overlays | v1.3 | 3/3 | Complete | 2026-02-15 |
| 22. Debug System Refinement | v1.3 | 1/1 | Complete | 2026-02-15 |
| 23. Item Entity Foundation | v1.4 | 2/2 | Complete | 2026-02-15 |
| 24. Pickup, Inventory Screen, and Loot Drops | v1.4 | 3/3 | Complete | 2026-02-16 |
| 25. Equipment Slots and Combat Integration | v1.4 | 0/4 | Not started | - |
| 26. Consumables and Polish | v1.4 | 0/TBD | Not started | - |
