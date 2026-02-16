# Phase 25: Equipment Slots and Combat Integration - Research

**Researched:** 2025-03-24
**Domain:** ECS Equipment Systems, Stat Modification Patterns, Combat Integration
**Confidence:** HIGH

## Summary

Phase 25 transitions the game's equipment system from stubs to a robust architecture using the **EffectiveStats pattern**. This ensures base character statistics remain untouched while equipment bonuses are dynamically calculated and applied.

Key components of this phase include:
1.  **Slot Management:** Implementing six standard slots (`head`, `body`, `main_hand`, `off_hand`, `feet`, `accessory`).
2.  **EffectiveStats Pattern:** Using an `EffectiveStats` component refreshed by an `EquipmentSystem` to store `base + modifiers`.
3.  **UI & Combat Integration:** Displaying the loadout in the sidebar and updating `CombatSystem` to prioritize `EffectiveStats`.

This approach prevents stat corruption and maintains a clean separation of concerns within the ECS.

**Primary recommendation:** Use a separate `EffectiveStats` component recomputed every frame by an `EquipmentSystem`. Update the `CombatSystem` to use helper methods that check for `EffectiveStats` before falling back to base `Stats`.

<user_constraints>
## User Constraints (from ROADMAP.md & REQUIREMENTS.md)

### Locked Decisions
- **Equipment Slots:** Must include `head`, `body`, `main_hand`, `off_hand`, `feet`, `accessory` (EQUIP-01).
- **EffectiveStats Pattern:** Effective stats must be computed as base stats + equipped bonuses each frame; base `Stats` values are never mutated by equip or unequip actions (EQUIP-04, Success Criterion 4).
- **Combat Integration:** `CombatSystem` must use `EffectiveStats` for all damage and defense calculations (EQUIP-05, Success Criterion 5).
- **UI Requirements:** Sidebar UI must display current equipment loadout with item names or "—" for empty slots (EQUIP-06, Success Criterion 3).
- **Input/Actions:** Pressing E (or Enter) on an item equips it; items remain in the `Inventory.items` list regardless of equipment status (Success Criterion 1). Pressing U (or dedicated key) unequips an item (EQUIP-03, Success Criterion 2).

### Claude's Discretion
- **Component naming:** Specific fields within `EffectiveStats` (beyond `power` and `defense`) are at Claude's discretion but should mirror `Stats` (e.g., `hp`, `max_hp`, `mana`, `max_mana`, `perception`, `intelligence`).
- **Implementation of Sidebar UI:** The specific layout/formatting in the sidebar is open for design.
- **Unequip key:** The exact key for unequipping from the loadout view (U is suggested).

### Deferred Ideas (OUT OF SCOPE)
- **Nested containers:** Only flat inventory is supported.
- **Item stacking:** Each item is a unique entity.
- **Drag-and-drop:** Arrow-key/keyboard navigation only.
- **Durability/Repair:** Deferred to future simulation milestones.
- **Crafting:** Out of scope for v1.4.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esper` | `3.x` | ECS Framework | Core of the existing game logic. |
| `dataclasses` | Stdlib | Component Definitions | Provides clean, typed data structures for ECS components. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `enum` | Stdlib | Slot Definitions | Use for `SlotType` to ensure type safety. |

## Architecture Patterns

### Pattern 1: Slot Management (Data-Driven)
**What:** Define the six required slots in an Enum and a mapping component on the bearer.
**Example:**
```python
class SlotType(str, Enum):
    HEAD = "head"
    BODY = "body"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    FEET = "feet"
    ACCESSORY = "accessory"

@dataclass
class Equipment:
    # Maps SlotType to entity ID
    slots: Dict[SlotType, Optional[int]] = field(default_factory=lambda: {
        s: None for s in SlotType
    })
```

### Pattern 2: EffectiveStats Pattern (Pre-computation)
**What:** `EquipmentSystem` iterates over entities with `Stats` and `Equipment`, summing `StatModifiers` from equipped items into a new `EffectiveStats` component.
**HP Logic:** `EffectiveStats.hp` uses `Stats.hp` (current health) as base. `EffectiveStats.max_hp` uses `Stats.base_max_hp` as base. `StatModifiers.hp` applies to BOTH.
**Run Order:** `EquipmentSystem` must run BEFORE `CombatSystem` each frame.

### Pattern 3: CombatSystem Helper Pattern
**What:** Encapsulate stat retrieval in helper methods to handle fallbacks cleanly.
**Example:**
```python
def _get_power(self, entity):
    eff = esper.try_component(entity, EffectiveStats)
    if eff: return eff.power
    stats = esper.try_component(entity, Stats)
    return stats.base_power if stats else 0
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stat Bookkeeping | Manual `+=` / `-=` | Full re-calculation | Eliminates state drift and irreversible errors. |
| Slot Validation | Multi-tag logic | Single `Equipment` map | Simplifies lookup and UI rendering. |

## Common Pitfalls

### Pitfall 1: Base Stat Redundancy
**What goes wrong:** `Stats` component has both `power` and `base_power`. If `CombatSystem` reads `power` while `EquipmentSystem` writes to `EffectiveStats.power`, the two go out of sync.
**Prevention:** Use `base_power` as the source of truth for the base, and `EffectiveStats` for the result. Ignore the legacy `power` field or sync it once at the end.

### Pitfall 2: Inventory Status Confusion
**What goes wrong:** Thinking equipped items move out of inventory.
**Prevention:** Remember that `Inventory.items` is the "master list" of all items owned by the entity. `Equipment.slots` only references entity IDs already present in that list.

### Pitfall 3: Stale References
**What goes wrong:** An item is dropped or destroyed but remains "equipped" in the `Equipment` component.
**Prevention:** `EquipmentSystem` should verify `world.entity_exists(item_id)` and ensure the item still has the `Equippable` component.

## Code Examples

### EffectiveStats Component
```python
# ecs/components.py
@dataclass
class EffectiveStats:
    hp: int
    max_hp: int
    power: int
    defense: int
    mana: int
    max_mana: int
    perception: int
    intelligence: int
```

### EquipmentSystem Logic (Simplified)
```python
# ecs/systems/equipment_system.py
class EquipmentSystem(esper.Processor):
    def process(self):
        for ent, (stats, equip) in esper.get_components(Stats, Equipment):
            # HP uses current health as base
            hp = stats.hp
            # Others use base_ values
            max_hp = stats.base_max_hp
            power = stats.base_power
            defense = stats.base_defense
            # ... sum other base stats ...
            
            for slot, item_eid in equip.slots.items():
                if item_eid and esper.entity_exists(item_eid):
                    mods = esper.try_component(item_eid, StatModifiers)
                    if mods:
                        # hp modifier applies to BOTH current and max
                        hp += mods.hp
                        max_hp += mods.hp
                        power += mods.power
                        defense += mods.defense
                        # ...
            
            # Update EffectiveStats component
            # ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Mutate `Stats` | `EffectiveStats` | Modern ECS | No irreversible state; easier testing. |
| Hardcoded Slots | Data-driven Map | Modular Design | Add new slots via data without changing classes. |

## Open Questions

1. **Accessory Slot Count:**
   - **What we know:** The requirement lists "accessory" (singular).
   - **What's unclear:** Will we need multiple accessory slots (e.g. 2 rings) later?
   - **Recommendation:** Stick to one `accessory` slot for now. The `Equipment` map makes adding `accessory_2` trivial later.

## Sources

### Primary (HIGH confidence)
- `ROADMAP.md` & `REQUIREMENTS.md` (v1.4 Milestone)
- `ecs/components.py` (Current `Stats` structure)
- `ecs/systems/combat_system.py` (Current combat logic)

### Secondary (MEDIUM confidence)
- General ECS Stat Modification patterns.

## Metadata
**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: HIGH

**Research date:** 2025-03-24
**Valid until:** 2025-04-24
