# Requirements: Rogue Like RPG — v1.4 Item & Inventory System

**Defined:** 2026-02-15
**Core Value:** Provide an engaging and replayable dungeon-crawling experience with strategic turn-based combat.

## v1 Requirements

Requirements for v1.4 milestone. Each maps to roadmap phases.

### Item Entity

- [ ] **ITEM-01**: Item exists as a full ECS entity with identity continuity across ground, inventory, and equipped states
- [ ] **ITEM-02**: Item templates are defined in JSON (items.json) and loaded via ItemRegistry/ItemFactory pipeline
- [ ] **ITEM-03**: Items on the ground are rendered on the map via existing RenderSystem
- [ ] **ITEM-04**: Items have weight (kg) used for carry capacity checks
- [ ] **ITEM-05**: Items have a material type (wood, metal, glass, etc.) stored as a component

### Inventory

- [ ] **INV-01**: Player can pick up items at their position with the G key
- [ ] **INV-02**: Pickup is rejected with a log message when over weight capacity
- [ ] **INV-03**: Player can open inventory screen with the I key (modal GameStates.INVENTORY)
- [ ] **INV-04**: Inventory screen lists carried items with arrow-key navigation
- [ ] **INV-05**: Player can drop items from inventory with the D key, restoring them to the map
- [ ] **INV-06**: Carried items survive map transitions (freeze/thaw entity closure)

### Equipment

- [ ] **EQUIP-01**: Equipment slots exist (head, body, main_hand, off_hand, feet, accessory)
- [ ] **EQUIP-02**: Player can equip items to matching slots from inventory
- [ ] **EQUIP-03**: Player can unequip items back to inventory
- [ ] **EQUIP-04**: Effective stats are computed as base stats + equipped bonuses each frame
- [ ] **EQUIP-05**: CombatSystem uses effective stats for damage calculation
- [ ] **EQUIP-06**: Current equipment loadout is visible in the sidebar UI

### Consumable & Loot

- [ ] **CONS-01**: Consumable items can be used from inventory (U key)
- [ ] **CONS-02**: Health potion restores HP on use and is destroyed afterward
- [ ] **CONS-03**: Monsters have contextual loot tables (wolves drop pelts, not gold)
- [ ] **CONS-04**: Loot items spawn at monster position on death via entity_died event
- [ ] **CONS-05**: Material type appears in item descriptions and investigation output

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Material Interactions

- **MATX-01**: Wood items catch fire when exposed to fire damage
- **MATX-02**: Metal items conduct electricity (lightning damage bonus)
- **MATX-03**: Glass items shatter on impact/drop from height

### Advanced Inventory

- **AINV-01**: Nested containers (bags-in-bags) with recursive weight calculation
- **AINV-02**: Identified/unidentified items with per-run name mapping
- **AINV-03**: Pick up all items at position (G key variant)

### Advanced Consumables

- **ACONS-01**: Mana restore consumable
- **ACONS-02**: Poison consumable
- **ACONS-03**: Teleport scroll consumable

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Nested containers (bags-in-bags) | Flat inventory sufficient for v1.4; adds recursive weight complexity |
| Item stacking (10x Health Potion) | Each item is a unique entity; stacking contradicts identity continuity |
| Drag-and-drop inventory UI | Requires mouse input system not yet built; arrow-key sufficient |
| Item durability/repair | Future simulation hook; not needed for core item loop |
| Crafting system | Independent milestone; too large for v1.4 scope |
| NPC economy/trading | Requires NPC interaction system not yet built |
| Auto-sort inventory | Low priority QoL; manual management sufficient |
| Item cursing/blessing | Adds UI affordances and content design beyond v1.4 scope |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ITEM-01 | Phase 23 | Pending |
| ITEM-02 | Phase 23 | Pending |
| ITEM-03 | Phase 23 | Pending |
| ITEM-04 | Phase 23 | Pending |
| ITEM-05 | Phase 23 | Pending |
| INV-06 | Phase 23 | Pending |
| INV-01 | Phase 24 | Pending |
| INV-02 | Phase 24 | Pending |
| INV-03 | Phase 24 | Pending |
| INV-04 | Phase 24 | Pending |
| INV-05 | Phase 24 | Pending |
| CONS-03 | Phase 24 | Pending |
| CONS-04 | Phase 24 | Pending |
| EQUIP-01 | Phase 25 | Pending |
| EQUIP-02 | Phase 25 | Pending |
| EQUIP-03 | Phase 25 | Pending |
| EQUIP-04 | Phase 25 | Pending |
| EQUIP-05 | Phase 25 | Pending |
| EQUIP-06 | Phase 25 | Pending |
| CONS-01 | Phase 26 | Pending |
| CONS-02 | Phase 26 | Pending |
| CONS-05 | Phase 26 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-15*
*Last updated: 2026-02-15 after roadmap creation*
