# Phase 23: Item Entity Foundation - Research

**Researched:** 2026-02-15
**Domain:** ECS Item System, Map Persistence, Stat Calculation
**Confidence:** HIGH

## Summary

This phase establishes items as first-class ECS entities. They will transition from static JSON templates to live entities that can exist on the ground (with a `Position` component) or in an inventory (without a `Position` component). To ensure items survive map transitions while carried by the player, we implement a "Transitive Closure" pattern to identify all entities that must be excluded from map-local freezing.

Furthermore, we introduce the "Effective Stats" pattern to support future equipment bonuses. This involves splitting `Stats` into base and current/effective values, allowing bonuses to be applied without destructive mutation of the base data.

**Primary recommendation:** Use a flyweight registry for item templates and a recursive closure helper for map transitions. Adopt a dual-field approach for `Stats` (e.g., `base_power` and `power`) to support non-destructive modifiers.

<user_constraints>
## User Constraints (from ROADMAP.md)

### Locked Decisions
- Items must exist as first-class ECS entities in the world and survive map transitions intact.
- Item templates must be defined in `assets/data/items.json` and loaded via a Registry/Factory pipeline.
- Each item must have a `Portable` component (weight) and an `ItemMaterial` component.
- `get_entity_closure(player_entity)` must be used to gather items for map transitions.
- Render pipeline must remain unchanged; items use the existing `RenderSystem`.

### Claude's Discretion
- Specific structure of `ItemTemplate` (fields and types).
- Implementation details of the `get_entity_closure` recursion.
- Exact strategy for "Effective Stats" field placement (prefixing vs. separate components).

### Deferred Ideas (OUT OF SCOPE)
- Pickup/Drop logic (Phase 24).
- Inventory UI (Phase 24).
- Equipment slot logic (Phase 25).
- Consumable effects (Phase 26).
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esper` | Current | ECS Engine | Project standard for entity management. |
| `pygame` | Current | Rendering | Project standard for sprite display. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `json` | Built-in | Data Loading | Used for `items.json` parsing. |

## Architecture Patterns

### Recommended Project Structure
```
entities/
├── item_registry.py  # ItemTemplate and ItemRegistry (Singleton)
└── item_factory.py   # ItemFactory (ECS entity creation)
assets/data/
└── items.json        # Item data definitions
```

### Pattern 1: Flyweight Registry & Factory
**What:** Mirroring `EntityRegistry` and `EntityFactory`, this separates immutable template data from live ECS entity state.
**When to use:** For all data-driven game objects (items, monsters, tiles).
**Example:**
```python
@dataclass
class ItemTemplate:
    id: str
    name: str
    sprite: str
    color: Tuple[int, int, int]
    weight: float
    material: str
    description: str
    stats: Dict[str, int] # e.g., {"power": 5}
```

### Pattern 2: Transitive Closure for Transitions
**What:** Recursive search to find all entities "owned" by a root entity (the player).
**When to use:** During `transition_map` to ensure carried items aren't deleted by the current map's `freeze()` call.
**Logic:**
1. Start with `root_entity`.
2. Check if it has an `Inventory` component.
3. If yes, add all entity IDs in `Inventory.items` to the set.
4. Recursively call for each newly added item (for nested containers).
5. Return the full set of IDs to be passed to `exclude_entities`.

### Pattern 3: Effective Stats (Dual-Field)
**What:** Storing both `base_value` and `effective_value` in the `Stats` component.
**Strategy:**
- `base_power`: The intrinsic value from the template.
- `power`: The current value after all modifiers (gear, buffs).
- Systems (Combat, UI) always read the effective field (`power`).
- A `StatCalculationSystem` (Phase 25) will be responsible for syncing them.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inventory Links | Custom ID mapping | `Inventory` component | `esper` handles entity lifecycle; lists of IDs are sufficient and survive freeze/thaw. |
| Item Persistence | Custom File Format | Existing `MapContainer.frozen_entities` | Items are entities; the existing freeze/thaw mechanism already handles component serialization. |

## Common Pitfalls

### Pitfall 1: Orphaned Entity IDs
**What goes wrong:** Carrying an entity ID in `Inventory.items` while the entity itself is deleted from the world by a map transition.
**How to avoid:** Use `get_entity_closure` to ensure all carried entities are added to `exclude_entities` during map `freeze()`.

### Pitfall 2: Static Stat Mutation
**What goes wrong:** Modifying `stats.power` directly when equipping a sword, then losing the base value forever when the sword is unequipped.
**How to avoid:** Always preserve `base_power` and treat `power` as a derived/calculated value.

### Pitfall 3: Sprite Layer Z-Fighting
**What goes wrong:** Items appearing behind floors or on top of players.
**How to avoid:** Explicitly use `SpriteLayer.ITEMS` (value 3), which is above `GROUND` (0) but below `ENTITIES` (5).

## Code Examples

### Item Template Definition (JSON)
```json
[
  {
    "id": "iron_sword",
    "name": "Iron Sword",
    "sprite": "/",
    "color": [192, 192, 192],
    "sprite_layer": "ITEMS",
    "weight": 2.0,
    "material": "iron",
    "description": "A sharp iron sword.",
    "stats": {
       "power": 5
    }
  }
]
```

### Closure Helper (Conceptual)
```python
def get_entity_closure(world, root_entity):
    closure = {root_entity}
    stack = [root_entity]
    
    while stack:
        current = stack.pop()
        if world.has_component(current, Inventory):
            inv = world.component_for_entity(current, Inventory)
            for item_id in inv.items:
                if item_id not in closure:
                    closure.add(item_id)
                    stack.append(item_id)
    return list(closure)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Object-based inventory | Entity-based items | Phase 23 | Items can have their own components (AI, LightSource, etc.) and exist independently in the world. |
| Direct Stat Mutation | Effective Stats Pattern | Phase 23 | Allows for temporary buffs and gear bonuses without losing character progression data. |

## Open Questions

1. **Stats for Items:** Should items have a `Stats` component or a `StatModifiers` component?
   - **Recommendation:** Use a dedicated `StatModifiers` component for items. This avoids confusion with the character's `Stats` and makes it clear that the item *provides* bonuses rather than having its own HP/Mana.
2. **Nesting Depth:** Do we support bags-within-bags?
   - **Recommendation:** The recursive closure logic supports it for free. No need to artificially limit it unless performance becomes an issue.

## Sources

### Primary (HIGH confidence)
- `entities/entity_registry.py` - Existing pattern for flyweight templates.
- `map/map_container.py` - `freeze`/`thaw` logic and `exclude_entities` parameter.
- `config.py` - Existing `SpriteLayer.ITEMS` enum.

### Secondary (MEDIUM confidence)
- "Effective Stats Pattern" - Common roguelike/RPG architecture for non-destructive modifiers.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Standard libraries used.
- Architecture: HIGH - Mirrors existing successful patterns in the codebase.
- Pitfalls: HIGH - Based on known ECS transition issues.

**Research date:** 2026-02-15
**Valid until:** 2026-03-15
