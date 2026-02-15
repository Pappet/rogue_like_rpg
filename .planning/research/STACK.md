# Stack Research

**Domain:** Item & inventory system — simulation-first rogue-like RPG (v1.4 milestone)
**Researched:** 2026-02-15
**Confidence:** HIGH (all findings verified live against Python 3.13.11, pygame 2.6.1, esper 3.7)

## Summary

No new external dependencies are needed. Every technical capability required — weighted loot
tables, material tags, equipment slot management, stat recalculation, inventory UI rendering,
scrollable panels — is covered by the existing stack (Python 3.13 stdlib + pygame 2.6.1 +
esper 3.7) and the project's established JSON pipeline pattern.

The work is entirely additive: new ECS components (dataclasses), an extended `items.json` data
file, a new `ItemFactory` following the `EntityFactory` pattern, and a new `InventorySystem`
drawn into the existing `GameStates.INVENTORY` modal state.

---

## Existing Stack (Validated — Do Not Re-Research)

| Technology | Installed Version | Role |
|------------|-------------------|------|
| Python | 3.13.11 | Runtime |
| PyGame | 2.6.1 (SDL 2.28.4) | Rendering, input, draw primitives |
| esper | 3.7 | ECS world, component queries |

**No version changes. No new packages.**

---

## Recommended Stack: New Capabilities

### Python 3.13 stdlib — All Verified Live

| API | Module | Purpose | Verification |
|-----|--------|---------|--------------|
| `random.choices(pool, weights, k)` | `random` | Weighted loot table rolls — 0.0013ms per roll at 10K iterations | Confirmed live |
| `random.seed(n)` | `random` | Deterministic loot for tests | Confirmed live |
| `bisect.bisect(cumulative, roll)` | `bisect` | Alternative CDF loot lookup (use only if n > 50 items in one table) | Confirmed live |
| `dataclasses.dataclass` + `field(default_factory=...)` | `dataclasses` | All new ECS components | Confirmed live |
| `enum.Enum` / `str, Enum` | `enum` | `SlotType`, `ItemType`, `MaterialTag` enums | Confirmed live |
| `typing.Optional`, `Dict`, `List`, `Set` | `typing` | Component type annotations | Confirmed live |
| `collections.OrderedDict` | `collections` | Equipment slot ordering (head → body → hands → feet) | Confirmed live |

**Loot table recommendation:** Use `random.choices(pool, weights=weights, k=1)[0]` directly.
It is C-implemented, requires no precomputation, and is fast enough for any rogue-like scale.
Do not implement a custom CDF class.

### esper 3.7 — Key APIs for Item System

All confirmed available and working:

| API | Purpose |
|-----|---------|
| `esper.create_entity(*components)` | Spawn item entity on ground (at drop, map load) |
| `esper.delete_entity(eid)` | Remove item entity when picked up |
| `esper.add_component(eid, component)` | Add `Equipped` marker on equip |
| `esper.remove_component(eid, ComponentType)` | Remove `Equipped` marker on unequip |
| `esper.try_component(eid, ComponentType)` | Safe optional lookup — returns `None` if missing (critical for items without all component types) |
| `esper.has_component(eid, ComponentType)` | Check slot occupancy, material presence |
| `esper.get_components(TypeA, TypeB)` | Query all items at a position (ground pickup scan) |
| `esper.component_for_entity(eid, Type)` | Direct lookup when entity known to have component |
| `esper.dispatch_event(name, data)` | `item_picked_up`, `item_equipped`, `item_consumed` events |
| `esper.set_handler(name, fn)` | Register inventory/equipment event handlers |

**Critical:** Use `esper.try_component()` — not `try/except KeyError` — for all optional item
component access. This is the correct esper 3.7 pattern and avoids exception overhead.

### pygame 2.6.1 — New UI Primitives for Inventory Panel

All confirmed working:

| API | Module | Purpose |
|-----|--------|---------|
| `pygame.Surface((w,h), pygame.SRCALPHA)` | `pygame` | Dim overlay under inventory modal |
| `dim.fill((0, 0, 0, 180))` | `pygame.Surface` | 70% opaque background dim |
| `panel.subsurface(rect)` | `pygame.Surface` | Clipped scrollable item list within panel |
| `font.size(text)` | `pygame.font.Font` | Measure item name width for column layout |
| `font.get_linesize()` | `pygame.font.Font` | Consistent row height (16px at size 14) |
| `rect.collidepoint(mouse_pos)` | `pygame.Rect` | Mouse hover detection over inventory rows |
| `pygame.draw.rect(surface, color, rect)` | `pygame.draw` | Row highlight, panel borders, equipment slot boxes |
| `pygame.draw.line(surface, color, p1, p2)` | `pygame.draw` | Column separators |
| `pygame.key.get_pressed()` | `pygame` | Held-key scroll in long inventory lists |

**Scrolling strategy:** Track `scroll_offset: int` as item-row index. Render only rows where
`row_index >= scroll_offset` and `row_index < scroll_offset + visible_rows`. Do not use
`pygame.Surface.scroll()` (it moves pixel data, not a logical offset).

---

## New ECS Components Required

These are pure Python dataclasses added to `ecs/components.py`:

### Item Identity (required on all item entities)

```python
@dataclass
class Item:
    item_id: str          # registry key, e.g. "iron_sword"
    weight: float         # kg, used for carry-weight tracking

@dataclass
class ItemName:
    name: str
    description: str = ""
```

**Why separate `ItemName` from existing `Name`:** `Name` is used by AI entities (displayed in
combat log with color markup). Items need a separate description field and different display
context. Reusing `Name` would pollute the combat entity query namespace.

### Equipment

```python
from typing import Optional

class SlotType(str, Enum):
    HEAD      = "head"
    BODY      = "body"
    MAIN_HAND = "main_hand"
    OFF_HAND  = "off_hand"
    FEET      = "feet"
    ACCESSORY = "accessory"

@dataclass
class Equippable:
    slot: SlotType
    power_bonus:   int = 0
    defense_bonus: int = 0

@dataclass
class Equipment:
    """On the bearer entity (player/NPC). Maps slot → item entity ID."""
    slots: Dict[str, Optional[int]] = field(
        default_factory=lambda: {s.value: None for s in SlotType}
    )
    # Cached bonus totals — recomputed on equip/unequip, not every frame
    power_bonus:   int = 0
    defense_bonus: int = 0
```

**Stat recalculation pattern:** When equipping/unequipping, iterate all equipped item entities,
sum their `Equippable` bonuses, write totals back to `Equipment.power_bonus` /
`Equipment.defense_bonus`. Combat system reads `Stats.base_power + equipment.power_bonus`.
Do NOT modify `Stats` directly on equip — that makes unequip require saving old values.

### Inventory (weight-based flat list)

```python
@dataclass
class Inventory:
    items: List[int] = field(default_factory=list)  # item entity IDs
    max_weight: float = 50.0
    current_weight: float = 0.0

    def can_add(self, item_weight: float) -> bool:
        return self.current_weight + item_weight <= self.max_weight
```

**Why entity IDs not item data:** Items stay as full ECS entities in inventory (no Position
component while held). This allows items to retain all their components (material, equippable,
consumable) without duplicating the data structure. On pickup: remove `Position` component,
add entity ID to `Inventory.items`. On drop: restore `Position`, remove from list.

### Consumables

```python
class ConsumeEffect(str, Enum):
    HEAL       = "heal"
    RESTORE_MP = "restore_mp"
    POISON     = "poison"

@dataclass
class Consumable:
    effect: ConsumeEffect
    value: int            # HP/MP restored, or damage for poison
    charges: int = 1      # Depleted consumables → delete entity
```

### Material Properties

```python
class MaterialTag(str, Enum):
    FLAMMABLE   = "flammable"
    CONDUCTIVE  = "conductive"
    BRITTLE     = "brittle"
    METAL       = "metal"
    ORGANIC     = "organic"

@dataclass
class ItemMaterial:
    material_id: str              # e.g. "iron", "wood"
    tags: Set[str] = field(default_factory=set)

    def has_tag(self, tag: MaterialTag) -> bool:
        return tag.value in self.tags
```

**Why tags as `Set[str]` not `Set[MaterialTag]`:** JSON deserialization produces strings. Storing
as strings avoids a conversion step in the factory and keeps JSON human-readable. The `has_tag`
method accepts the enum for type-safe query sites.

---

## JSON Pipeline Integration

Follows the existing `entities.json` → `EntityRegistry` → `EntityFactory` pattern exactly.

### New file: `assets/data/items.json`

```json
[
  {
    "id": "iron_sword",
    "name": "Iron Sword",
    "sprite": "/",
    "color": [180, 180, 200],
    "sprite_layer": "ITEMS",
    "item_type": "weapon",
    "weight": 3.5,
    "equip_slot": "main_hand",
    "power_bonus": 5,
    "defense_bonus": 0,
    "material": "iron",
    "material_tags": ["metal", "conductive"],
    "description": "A standard iron sword"
  },
  {
    "id": "health_potion",
    "name": "Health Potion",
    "sprite": "!",
    "color": [255, 50, 50],
    "sprite_layer": "ITEMS",
    "item_type": "consumable",
    "weight": 0.5,
    "equip_slot": null,
    "effect": "heal",
    "effect_value": 10,
    "material": "glass",
    "material_tags": ["brittle"],
    "description": "Restores 10 HP"
  }
]
```

### New file: `assets/data/loot_tables.json`

```json
{
  "orc": [
    {"item_id": "iron_sword",    "weight": 15},
    {"item_id": "health_potion", "weight": 30},
    {"item_id": null,            "weight": 55}
  ]
}
```

`item_id: null` represents "no drop". Weight values are relative (not percentages). The loot
engine calls `random.choices(item_ids, weights=weights, k=1)`.

### New class: `entities/item_registry.py`

Mirror of `entity_registry.py`. Stores `ItemTemplate` dataclasses keyed by item ID.

### New class: `entities/item_factory.py`

Mirror of `entity_factory.py`. Creates item ECS entities from `ItemRegistry`. Conditionally
attaches `Equippable`, `Consumable`, `ItemMaterial` based on `item_type` field — same
conditional component attachment pattern used for `AI` and `Description` in `EntityFactory`.

### `services/resource_loader.py` extension

Add `ResourceLoader.load_items(filepath)` and `ResourceLoader.load_loot_tables(filepath)`.
Follow the existing `load_entities` validation pattern (required fields, type coercion,
enum validation with descriptive error messages).

---

## New Game State: `GameStates.INVENTORY`

Add to `config.py GameStates` enum:

```python
INVENTORY = 5
```

Inventory screen is a modal overlay: game world is rendered frozen behind a dimmed panel.
Do NOT freeze/thaw the ECS world — items need to remain accessible as entities during the
inventory screen. The `INVENTORY` state intercepts all keyboard input; arrow keys scroll the
list, Enter confirms use/equip, Escape closes.

**Why not a separate `GameState` class like `WorldMapState`:** The inventory screen needs
direct access to player entity component data (Stats, Equipment, Inventory). A modal state
within the existing `Game` state avoids the persist dictionary round-trip and keeps component
access direct.

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pygame_gui` or `pygame-menu` | External UI library with its own event loop; overkill for a flat list with 20-30 items | `pygame.draw.rect` + `pygame.font.SysFont` + `surface.subsurface` — matches existing UI system |
| `numpy` for weight arithmetic | 2D float arithmetic on <100 items; numpy import overhead exceeds any speedup | Python `float` arithmetic — inventory weight sums are 3-4 additions |
| A separate `ItemComponent` base class or ABC | Python ECS is component-by-presence, not component-by-inheritance; base classes add coupling with zero benefit | Flat dataclasses; use `esper.has_component(eid, Equippable)` to check capability |
| `pickle` or `shelve` for save state | Not requested; adds serialization complexity; JSON pipeline already handles data | If save/load is added later, extend the JSON pipeline |
| Custom weighted-random class | `random.choices` is C-implemented, 0.0013ms/call, already in stdlib | `random.choices(pool, weights=weights, k=1)[0]` |
| `attr`/`pydantic` for item templates | `dataclasses` is already used for all components; introducing a second validation library for item templates creates inconsistency | Extend `dataclasses` pattern; validate in `ResourceLoader.load_items()` |
| Per-slot `Component` classes (e.g. `HeadSlot`, `BodySlot`) | Creates 6 component types for one concept; queries become `has_component(e, HeadSlot) or has_component(e, BodySlot)` | Single `Equipment` dataclass with `Dict[str, Optional[int]]` slot map |
| `pygame.sprite.Group` for item rendering | Items are ECS entities rendered by existing `RenderSystem`; `SpriteLayer.ITEMS` (value 3) already defined in `config.py` | Existing `RenderSystem` with `SpriteLayer.ITEMS` — zero new rendering code for ground items |

---

## Integration Points

### `SpriteLayer.ITEMS` already defined

`config.py` line 37: `ITEMS = 3`. Ground items render between `TRAPS` (2) and `CORPSES` (4).
The existing `RenderSystem` will render item entities automatically — no changes to
`RenderSystem` needed. Set `Renderable.layer = SpriteLayer.ITEMS.value` in `ItemFactory`.

### `Stats` component — add base fields

Current `Stats` has `power` and `defense`. For equipment bonuses, add `base_power` and
`base_defense` fields to hold the unmodified values:

```python
@dataclass
class Stats:
    hp: int
    max_hp: int
    power: int          # effective = base + equipment bonus (computed field, not stored)
    defense: int        # effective = base + equipment bonus
    mana: int
    max_mana: int
    perception: int
    intelligence: int
    base_power: int = 0      # NEW: set equal to power on entity creation
    base_defense: int = 0    # NEW: set equal to defense on entity creation
```

`CombatSystem` uses `stats.power` directly today. After this change, it should use
`stats.base_power + (equipment.power_bonus if equipment else 0)`. The existing `power` field
can be kept as the effective cached value if preferred over inline addition.

### Event system — new events to register

| Event | When dispatched | Handler location |
|-------|-----------------|------------------|
| `item_picked_up` | Player steps on item and picks it up | `UISystem` (log message) |
| `item_dropped` | Item removed from inventory to ground | `UISystem` (log message) |
| `item_equipped` | Item moved from inventory to slot | `UISystem`, stat recalculator |
| `item_unequipped` | Item moved from slot back to inventory | `UISystem`, stat recalculator |
| `item_consumed` | Consumable used; apply effect | `ConsumableSystem` or inline in action handler |
| `loot_dropped` | Enemy death drops items on ground | `DeathSystem` triggers loot roll |

Wired via `esper.set_handler` following existing `log_message` pattern in `UISystem.__init__`.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Loot probability | `random.choices(pool, weights)` | Custom CDF class with `bisect` | `random.choices` is C-level and already meets performance needs; custom class adds 30 lines for zero gain |
| Equipment slots | `Dict[str, Optional[int]]` in `Equipment` dataclass | Separate `HeadSlot`, `BodySlot` etc. components | Per-slot components scatter slot state across 6 component queries; dict is O(1) and introspectable |
| Stat bonuses | Cached bonus totals in `Equipment`, recomputed on equip events | Recalculate every frame in a system | Per-frame recalculation wastes CPU summing item bonuses every tick; event-driven cache is O(1) during combat |
| Inventory UI rendering | Modal overlay within `Game` state | Separate `GameState` subclass like `WorldMapState` | Modal needs live component access; separate state requires serializing inventory state through `persist` dict |
| Item entity lifecycle | Items are ECS entities; remove `Position` on pickup | Separate `ItemData` dataclass stored in `Inventory.items` | ECS-as-entity preserves all item components (material, equippable) without a parallel data structure |
| Material interactions | `Set[str]` tags on `ItemMaterial` component | Separate `Flammable`, `Conductive`, `Brittle` components | Tag set queries `mat.has_tag(MaterialTag.X)` vs `esper.has_component(eid, Flammable)` — the former keeps all material logic in one place without polluting the component namespace |

---

## Installation

No new packages.

```bash
# Verify existing stack (all confirmed working):
python3 -c "import pygame; print(pygame.__version__)"    # 2.6.1
python3 -c "import esper; print(esper.__version__)"      # 3.7
python3 -c "import random; random.choices(['a','b'], weights=[1,2], k=1)"  # stdlib ok
python3 -c "from dataclasses import dataclass, field; print('ok')"         # stdlib ok
```

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| Python | 3.13.11 | All stdlib modules used | `random.choices` available since 3.6 |
| PyGame | 2.6.1 | Python 3.13.11 | `surface.subsurface`, `Rect.collidepoint`, `font.size()` all confirmed |
| esper | 3.7 | Python 3.13.11 | `try_component`, `get_components`, `delete_entity` all confirmed available |

---

## Sources

- Live codebase inspection:
  - `ecs/components.py`: existing `Stats`, `Inventory`, `Name`, `Action` component shapes — confirmed
  - `entities/entity_factory.py`: conditional component attachment pattern — confirmed
  - `services/resource_loader.py`: JSON validation + registry population pattern — confirmed
  - `config.py`: `SpriteLayer.ITEMS = 3` already defined — confirmed, line 37
  - `ecs/systems/ui_system.py`: `pygame.font.SysFont`, `pygame.draw.rect` pattern — confirmed
  - `game_states.py`: `GameStates` enum, event wiring, modal state pattern — confirmed
  — HIGH confidence, read directly from source

- Live API verification (Python 3.13.11, pygame 2.6.1, esper 3.7):
  - `random.choices` weighted sampling: 0.0013ms/call at 10K iterations — confirmed
  - `esper.try_component` returns `None` on missing (not `KeyError`) — confirmed
  - `esper.get_components(TypeA, TypeB)` multi-component query — confirmed
  - `esper.delete_entity` / `add_component` / `remove_component` — all confirmed
  - `pygame.Surface.subsurface(rect)` for clipped list rendering — confirmed
  - `pygame.font.Font.get_linesize()` returns 16px at font size 14 — confirmed
  - `pygame.Rect.collidepoint(pos)` for mouse hover — confirmed
  - Material tag system with `Set[str]` + `str, Enum` — confirmed working
  — HIGH confidence, all verified against running process

---
*Stack research for: Item & inventory system — rogue-like RPG v1.4 milestone*
*Researched: 2026-02-15*
