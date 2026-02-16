# Phase 26: Consumables and Polish - Research

**Researched:** 2024-03-24
**Domain:** Game Mechanics (Consumables), UI Polish (Inspections)
**Confidence:** HIGH

## Summary

This phase focuses on the implementation of consumable items and enhancing the descriptive depth of item inspections. The core task is to enable items like "Health Potions" to provide immediate benefits when used from the inventory and to ensure that the physical nature (material) of items is visible to the player during inspection.

The current ECS architecture already provides `Stats`, `Inventory`, and `ItemMaterial` components. This phase will build upon these by introducing a `Consumable` component and a `ConsumableService` to handle the logic of item usage, turn consumption, and logging. Descriptions will be made dynamic by aggregating data from `Description` and `ItemMaterial` components.

**Primary recommendation:** Implement a `Consumable` component to store effect data (e.g., `effect_type`, `amount`) and create a `ConsumableService` that modifies `Stats` and handles item removal from `Inventory`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.10+ | Language | Project base |
| Esper | 3.2+ | ECS Framework | Core architecture |
| Pygame | 2.5+ | Rendering/Input | Core engine |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Dataclasses | Built-in | Component definition | Standard ECS pattern |

**Installation:**
No new packages required.

## Architecture Patterns

### Recommended Project Structure
```
ecs/
├── components.py    # Add Consumable component
services/
├── consumable_service.py # Logic for using items
entities/
├── item_factory.py  # Update to handle Consumable data
assets/data/
├── items.json       # Add consumable properties to templates
```

### Pattern 1: Service-Based Consumption
**What:** Centralizing the logic for "using" an item into a service.
**When to use:** When an action (like using a potion) needs to check requirements, modify stats, log results, and update inventory.
**Example:**
```python
class ConsumableService:
    @staticmethod
    def use_item(world, user_ent, item_ent):
        consumable = world.component_for_entity(item_ent, Consumable)
        stats = world.component_for_entity(user_ent, Stats)
        
        if consumable.effect_type == "heal_hp":
            old_hp = stats.hp
            stats.hp = min(stats.base_max_hp, stats.hp + consumable.amount)
            healed = stats.hp - old_hp
            esper.dispatch_event("log_message", f"You use the potion and heal {healed} HP.")
            
        # Remove from inventory if consumed
        if consumable.consumed_on_use:
            inv = world.component_for_entity(user_ent, Inventory)
            inv.items.remove(item_ent)
            world.delete_entity(item_ent)
```

### Anti-Patterns to Avoid
- **In-place Logic in UI:** Don't put the healing logic directly inside `InventoryState.get_event`. Use a service.
- **Direct EffectiveStats Modification:** Avoid modifying `EffectiveStats` directly for permanent healing. Modify the base `Stats.hp` and let `EquipmentSystem` recalculate.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rich Text Rendering | Custom parser | `MessageLog` | Already supports `[color=...]` tags. |
| Stat Recalculation | Manual updates | `EquipmentSystem` | It already handles `EffectiveStats` based on `Stats`. |

## Common Pitfalls

### Pitfall 1: Over-healing
**What goes wrong:** Using a potion at full health or healing past max HP.
**How to avoid:** Use `min(stats.base_max_hp, stats.hp + amount)` when applying healing.

### Pitfall 2: Inventory Desync
**What goes wrong:** Removing an item from the entity list but forgetting to remove it from the `Inventory.items` list.
**How to avoid:** Ensure the service handles both `inventory.items.remove()` and `world.delete_entity()`.

### Pitfall 3: Turn Economy Leak
**What goes wrong:** Player uses items without it costing a turn.
**How to avoid:** Explicitly call `turn_system.end_player_turn()` after a successful consumption.

## Code Examples

### Consumable Component Definition
```python
@dataclass
class Consumable:
    effect_type: str  # "heal_hp", "heal_mana"
    amount: int
    consumed_on_use: bool = True
```

### Dynamic Inspection Logic
```python
# In ActionSystem.confirm_action (inspect mode)
desc_comp = esper.try_component(ent, Description)
mat_comp = esper.try_component(ent, ItemMaterial)
port_comp = esper.try_component(ent, Portable)

desc_parts = []
if desc_comp:
    desc_parts.append(desc_comp.get(ent_stats))
if mat_comp:
    desc_parts.append(f"Material: {mat_comp.material}")
if port_comp:
    desc_parts.append(f"Weight: {port_comp.weight}kg")

full_desc = ". ".join(desc_parts)
esper.dispatch_event("log_message", f"[color=white]{name_comp.name}[/color]: {full_desc}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hardcoded Item Effects | Component-driven Effects | Phase 26 | Modular and data-driven items |
| Static Descriptions | Aggregated Inspection Data | Phase 26 | Richer world feedback |

## Open Questions

1. **Hotkey for Use:** Should we use `U` for Use and `E` for Equip?
   - **Recommendation:** Yes, `U` is standard. `Enter` can remain "Smart Interact" (Equip if equippable, Use if consumable).
2. **Multiple Effects:** Do we need items that have multiple effects (e.g., heal HP and Mana)?
   - **Recommendation:** Not required by CONS-01/02, but the `Consumable` component could be extended to a list of effects later.

## Sources

### Primary (HIGH confidence)
- `ecs/components.py` - Existing `ItemMaterial` and `Stats` structure.
- `ecs/systems/equipment_system.py` - Understanding of `EffectiveStats` calculation.
- `ui/message_log.py` - Rich text support.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Using project defaults.
- Architecture: HIGH - Fits existing service/component pattern.
- Pitfalls: HIGH - Common roguelike logic.

**Research date:** 2024-03-24
**Valid until:** 2024-04-24
