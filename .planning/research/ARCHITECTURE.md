# Architecture Research

**Domain:** Roguelike RPG — Item & Inventory System Integration with Existing ECS
**Researched:** 2026-02-15
**Confidence:** HIGH (based on direct codebase analysis — all integration points verified against source)

## Standard Architecture

### System Overview

```
game_states.py Game state machine
┌──────────────────────────────────────────────────────────────────────────┐
│  PLAYER_TURN → ENEMY_TURN → PLAYER_TURN ...                              │
│                                                                           │
│  + INVENTORY state (new)     ← new state: full-screen inventory screen  │
│  + TARGETING (existing)      ← unchanged                                 │
└──────────────────────────────────────────────────────────────────────────┘

Item Entity Lifecycle:
┌────────────────┐  pick up   ┌────────────────────────────────────────┐
│  On Ground     │ ─────────► │  In Inventory                          │
│  has Position  │            │  no Position, owner ref via Contained  │
│  SpriteLayer   │            │  component on item entity              │
│  ITEMS = 3     │            └────────────────────────────────────────┘
└────────────────┘                           │ equip
        ▲                                    ▼
        │ drop              ┌────────────────────────────────────────┐
        └───────────────────│  Equipped                              │
                            │  Equippable.equipped_by = owner_eid   │
                            │  StatModifier component applies bonus  │
                            └────────────────────────────────────────┘
```

### Component Responsibilities

**New Components (add to `ecs/components.py`):**

| Component | Responsibility | Notes |
|-----------|----------------|-------|
| `Portable` | Tag: entity can be picked up. Optional `weight: float = 1.0`. | Items on ground, in inventory, or equipped all have this. |
| `Contained` | Links item to its container entity. `owner: int`, `slot: str = "pack"`. | On item entity. `owner` is the entity whose `Inventory` holds this item. `slot` = "pack" or equipment slot name. |
| `Equippable` | Defines equipment slot and stat bonuses. `slot: str`, `bonus_power: int = 0`, `bonus_defense: int = 0`, etc. | Presence means item can be equipped. Separate from `Contained`. |
| `Consumable` | Defines use effect. `effect: str`, `magnitude: int`, `charges: int = 1`. | Item is used up (or loses charges) on activation. |
| `ItemMaterial` | `material: str` (e.g. "iron", "wood", "leather"). | Optional. Enables material-based descriptions and future resistances. |

**Modified Components:**

| Component | Change | Why |
|-----------|--------|-----|
| `Inventory` (existing stub) | Change `items: List` to `items: List[int]` — explicit list of entity IDs. Keep existing empty default. | Already stubbed correctly. The field is already `List` — just needs type annotation tightening and usage. |
| `Stats` (existing) | No structural change. Combat system reads `Stats` directly. Equipment bonuses are computed separately, not stored here. | Avoids corrupting base stats on equip/unequip. See Pattern 2 below. |

**Existing components that integrate unchanged:**

| Component | Role in Item System |
|-----------|---------------------|
| `Position` | Items on the ground have `Position`. Items in inventory do NOT have `Position`. This is the primary location signal. |
| `Renderable` | Items on ground rendered via `SpriteLayer.ITEMS` (value = 3, already in `config.py`). Items in inventory are not rendered by `RenderSystem`. |
| `Name` | Item display name. Already used by inspect system. |
| `Description` | Item flavor text. Already used by `ActionSystem.confirm_action()` inspect mode. |
| `Blocker` | Items on ground do NOT have `Blocker`. Items never block movement. |

---

## Location Resolution: Position vs. Contained

**The central design decision:** An item entity is in exactly one of three states:

```
State 1: On Ground
  has Position(x, y, layer)
  has Renderable
  no Contained component

State 2: In Inventory (pack)
  no Position component
  has Contained(owner=<entity_id>, slot="pack")
  no Renderable (or Renderable kept but ignored by RenderSystem filter)

State 3: Equipped
  no Position component
  has Contained(owner=<entity_id>, slot="weapon"|"armor"|"offhand"|...)
  has Equippable (pre-existing, defines what slot it goes in)
```

**Why no Position when carried:**
- `RenderSystem` and `MovementSystem` query `(Position, Renderable)`. Removing `Position` from carried items is the cleanest filter — no system accidentally renders or moves an item in someone's pack.
- Alternative (keeping Position, adding `InInventory` tag) was considered and rejected: it requires every system to check for the tag, not just the item-specific systems.

**Pick-up flow:**
1. Player moves onto item tile (or uses "Get" action).
2. `PickupSystem` runs: removes `Position` from item, removes `Renderable` from item, adds `Contained(owner=player_eid, slot="pack")` to item, appends item entity ID to `Inventory.items` on player.
3. Dispatch `"log_message"` event.

**Drop flow:**
1. Player selects item in inventory UI, chooses "Drop".
2. `PickupSystem` (or `ItemActionSystem`): removes `Contained`, adds `Position(player.x, player.y, player.layer)`, adds `Renderable(item_sprite, SpriteLayer.ITEMS.value, item_color)`, removes item ID from `Inventory.items`.

---

## Equipment and Stat Bonuses

### Pattern 2: Computed Stats via EquipmentSystem — Do Not Modify Base Stats

**Problem:** `Stats` is a flat dataclass with integer fields. If equipment adds `+3 defense` by mutating `stats.defense`, the base value is lost. Unequipping becomes a bookkeeping nightmare.

**Solution:** Keep `Stats` as **base stats only**. Add an `EquipmentSystem` that computes **effective stats** at query time, or pre-computes a `EffectiveStats` component each turn.

**Preferred approach for this codebase size:** Pre-compute `EffectiveStats` as a separate component, updated by `EquipmentSystem` each turn before `CombatSystem` runs.

```python
# New component in ecs/components.py
@dataclass
class EffectiveStats:
    power: int
    defense: int
    # Add other stat fields that equipment can modify
    # Does NOT store hp/mana (those remain on Stats)
```

```python
# EquipmentSystem (new system)
class EquipmentSystem(esper.Processor):
    def process(self):
        for ent, (stats,) in esper.get_components(Stats):
            base_power = stats.power
            base_defense = stats.defense
            bonus_power = 0
            bonus_defense = 0
            # Sum bonuses from all equipped items
            for item_eid, (contained, equippable) in esper.get_components(Contained, Equippable):
                if contained.owner == ent and contained.slot != "pack":
                    bonus_power += equippable.bonus_power
                    bonus_defense += equippable.bonus_defense
            # Write (or update) EffectiveStats
            if esper.has_component(ent, EffectiveStats):
                eff = esper.component_for_entity(ent, EffectiveStats)
                eff.power = base_power + bonus_power
                eff.defense = base_defense + bonus_defense
            else:
                esper.add_component(ent, EffectiveStats(
                    power=base_power + bonus_power,
                    defense=base_defense + bonus_defense
                ))
```

**CombatSystem change:** Change `attacker_stats.power` → `attacker_eff.power` and `target_stats.defense` → `target_eff.defense`. Fall back to `Stats` if no `EffectiveStats` present (handles non-equipped entities safely).

```python
# CombatSystem — modified damage calculation
def process(self):
    for attacker, intent in list(esper.get_component(AttackIntent)):
        target = intent.target_entity
        try:
            attacker_power = self._get_power(attacker)
            target_defense = self._get_defense(target)
            damage = max(0, attacker_power - target_defense)
            ...

def _get_power(self, entity) -> int:
    eff = esper.try_component(entity, EffectiveStats)
    if eff:
        return eff.power
    stats = esper.try_component(entity, Stats)
    return stats.power if stats else 0

def _get_defense(self, entity) -> int:
    eff = esper.try_component(entity, EffectiveStats)
    if eff:
        return eff.defense
    stats = esper.try_component(entity, Stats)
    return stats.defense if stats else 0
```

**Run order:** `EquipmentSystem` must process BEFORE `CombatSystem` each frame. Register it first in `game_states.py`.

---

## Item Entity Creation via JSON Pipeline

### Pattern 3: Separate ItemRegistry — Do Not Bolt Items onto EntityTemplate

**Why not reuse EntityTemplate for items:**
- `EntityTemplate` has `hp`, `max_hp`, `power`, `defense`, `mana`, `max_mana`, `perception`, `intelligence`, `ai`, `blocker`, `default_state`, `alignment` — all creature fields.
- Items have none of these. Forcing items through `EntityTemplate` creates a dataclass with ~12 meaningless zero fields plus item-specific fields shoehorned in.
- The conditional-attachment pattern in `EntityFactory` (`if template.ai: ...`) would explode with item-specific branches.

**Recommended approach:** Add `ItemTemplate` dataclass to `entities/entity_registry.py` (or a new `entities/item_registry.py`), and `ItemFactory` in `entities/entity_factory.py` (or `entities/item_factory.py`).

```python
# entities/item_registry.py — new file
from dataclasses import dataclass, field
from typing import Tuple, Dict

@dataclass
class ItemTemplate:
    id: str
    name: str
    sprite: str
    color: Tuple[int, int, int]
    description: str = ""
    # Portable
    weight: float = 1.0
    # Equippable (optional)
    equippable: bool = False
    equip_slot: str = ""          # "weapon", "armor", "offhand", "ring", etc.
    bonus_power: int = 0
    bonus_defense: int = 0
    # Consumable (optional)
    consumable: bool = False
    effect: str = ""              # "heal", "damage", "mana_restore", etc.
    magnitude: int = 0
    charges: int = 1
    # Material (optional)
    material: str = ""

class ItemRegistry:
    _registry: Dict[str, ItemTemplate] = {}

    @classmethod
    def register(cls, template: ItemTemplate) -> None:
        cls._registry[template.id] = template

    @classmethod
    def get(cls, template_id: str):
        return cls._registry.get(template_id)

    @classmethod
    def clear(cls):
        cls._registry.clear()
```

**JSON file:** `assets/data/items.json` — parallel to `entities.json`.

```json
[
  {
    "id": "iron_sword",
    "name": "Iron Sword",
    "sprite": "/",
    "color": [180, 180, 200],
    "description": "A well-worn iron sword.",
    "weight": 3.0,
    "equippable": true,
    "equip_slot": "weapon",
    "bonus_power": 3,
    "material": "iron"
  },
  {
    "id": "health_potion",
    "name": "Health Potion",
    "sprite": "!",
    "color": [255, 0, 0],
    "description": "A small vial of red liquid.",
    "consumable": true,
    "effect": "heal",
    "magnitude": 20,
    "charges": 1
  }
]
```

**ResourceLoader extension:** Add `ResourceLoader.load_items(filepath)` as a static method, parallel to `load_entities()`. Load into `ItemRegistry`. Call during startup in `main.py`.

**ItemFactory:** Creates item entity in world with Position (on ground) or without (spawning directly into an inventory).

```python
# entities/item_factory.py — new file
import esper
from config import SpriteLayer
from ecs.components import Renderable, Name, Description, Portable, Equippable, Consumable, ItemMaterial, Contained
from entities.item_registry import ItemRegistry

class ItemFactory:
    @staticmethod
    def create_on_ground(world, template_id: str, x: int, y: int, layer: int = 0) -> int:
        """Spawn item at map position."""
        template = ItemRegistry.get(template_id)
        if template is None:
            raise ValueError(f"Item template '{template_id}' not found.")

        components = [
            Position(x, y, layer),
            Renderable(template.sprite, SpriteLayer.ITEMS.value, template.color),
            Name(template.name),
            Portable(weight=template.weight),
        ]
        if template.description:
            components.append(Description(base=template.description))
        if template.equippable:
            components.append(Equippable(
                slot=template.equip_slot,
                bonus_power=template.bonus_power,
                bonus_defense=template.bonus_defense,
            ))
        if template.consumable:
            components.append(Consumable(
                effect=template.effect,
                magnitude=template.magnitude,
                charges=template.charges,
            ))
        if template.material:
            components.append(ItemMaterial(material=template.material))

        return world.create_entity(*components)

    @staticmethod
    def create_in_inventory(world, template_id: str, owner_eid: int) -> int:
        """Spawn item directly into an owner's inventory (no Position)."""
        template = ItemRegistry.get(template_id)
        if template is None:
            raise ValueError(f"Item template '{template_id}' not found.")

        components = [
            Name(template.name),
            Portable(weight=template.weight),
            Contained(owner=owner_eid, slot="pack"),
        ]
        if template.description:
            components.append(Description(base=template.description))
        if template.equippable:
            components.append(Equippable(
                slot=template.equip_slot,
                bonus_power=template.bonus_power,
                bonus_defense=template.bonus_defense,
            ))
        if template.consumable:
            components.append(Consumable(
                effect=template.effect,
                magnitude=template.magnitude,
                charges=template.charges,
            ))
        if template.material:
            components.append(ItemMaterial(material=template.material))

        item_eid = world.create_entity(*components)
        inv = esper.component_for_entity(owner_eid, Inventory)
        inv.items.append(item_eid)
        return item_eid
```

---

## Loot Drops and DeathSystem Integration

### Pattern 4: DeathSystem Dispatches "entity_died" — LootSystem Listens

**Do NOT modify `DeathSystem` to spawn loot inline.** It already dispatches `"entity_died"` and the handler is cleanly bounded.

**Add a `LootSystem`** that registers a handler for `"entity_died"` and queries the dead entity's `LootTable` component to spawn items.

```python
# New component
@dataclass
class LootTable:
    entries: List[dict]
    # Each entry: {"item_id": "iron_sword", "chance": 0.5, "count": 1}
```

```python
# ecs/systems/loot_system.py — new file
import esper
import random
from ecs.components import Position, LootTable
from entities.item_factory import ItemFactory

class LootSystem(esper.Processor):
    def __init__(self):
        esper.set_handler("entity_died", self.on_entity_died)

    def on_entity_died(self, entity):
        try:
            pos = esper.component_for_entity(entity, Position)
            loot_table = esper.component_for_entity(entity, LootTable)
        except KeyError:
            return  # No position or no loot table — nothing to drop

        for entry in loot_table.entries:
            if random.random() < entry.get("chance", 1.0):
                count = entry.get("count", 1)
                for _ in range(count):
                    ItemFactory.create_on_ground(
                        esper,
                        entry["item_id"],
                        pos.x,
                        pos.y,
                        pos.layer
                    )

    def process(self):
        pass
```

**EntityTemplate extension for loot:** Add `loot_table: List[dict] = field(default_factory=list)` to `EntityTemplate`. `EntityFactory.create()` attaches `LootTable(entries=template.loot_table)` if `template.loot_table` is non-empty. This matches the existing conditional-attachment pattern exactly.

**JSON example:**
```json
{
  "id": "orc",
  ...existing fields...,
  "loot_table": [
    {"item_id": "iron_sword", "chance": 0.3, "count": 1},
    {"item_id": "health_potion", "chance": 0.5, "count": 1}
  ]
}
```

---

## Freeze/Thaw and Inventoried Items

### Critical Pattern 5: Items in Inventory Must Freeze/Thaw with Their Owner

**The problem:** `MapContainer.freeze()` calls `world.delete_entity(ent)` for all entities not in `exclude_entities`. Item entities in inventories have no `Position` component, so they exist in the esper world but are invisible to any position-based filter. They will be deleted by `freeze()` if not handled.

**Solution:** When freezing, additionally exclude all item entities that are referenced in any `Inventory.items` list.

This means `MapContainer.freeze()` needs to know which entities to exclude beyond the player. Two options:

**Option A (recommended):** The caller (`Game.transition_map()`) computes the full exclusion list before calling `freeze()`.

```python
# In game_states.py — transition_map()
def _collect_carried_items(self, owner_entity):
    """Recursively collect all entity IDs in owner's inventory."""
    carried = []
    try:
        inv = esper.component_for_entity(owner_entity, Inventory)
        for item_eid in inv.items:
            carried.append(item_eid)
            # If items can contain items (bags), recurse here
    except KeyError:
        pass
    return carried

# Then in transition_map():
carried_items = self._collect_carried_items(self.player_entity)
exclusions = [self.player_entity] + carried_items
self.map_container.freeze(self.world, exclude_entities=exclusions)
```

**Option B:** `MapContainer.freeze()` auto-detects carried items by checking for `Inventory` components. This puts inventory logic in `map_container.py`, which is a layer violation — map container should not know about item systems. Use Option A.

**Thaw is safe:** When `thaw()` restores entities from `frozen_entities`, item entities that were frozen with the map will be restored into the world. Item entities that were excluded (carried items) remain in the world throughout — they are never deleted.

**What gets frozen with the map:**
- Monster entities on the map (they have `Position` pointing to this map)
- Items on the ground (they have `Position` pointing to this map)
- Corpses (they have `Position`)

**What is excluded from freezing:**
- Player entity (currently excluded by name)
- All items in player's `Inventory.items` list
- All items with `Contained(owner=player_eid, slot!="pack")` (equipped items)

**Edge case — equipped items on frozen NPCs:** NPCs do not typically carry inventories in this architecture. If an NPC has carried items in a future extension, those items' `Contained` components reference the NPC entity ID. After thaw, the NPC entity ID changes (esper reassigns IDs on `create_entity()`). This is a known limitation: NPC inventories require ID remapping on thaw, which is complex. Defer NPC inventories until after player inventory is working.

---

## Inventory UI and Game State Machine

### Pattern 6: INVENTORY as a New GameStates Value — Same Pattern as TARGETING

**Existing pattern:** `GameStates.TARGETING` is a value in the `GameStates` enum. `TurnSystem.current_state` is set to `TARGETING` when targeting starts, and `Game.get_event()` routes to `handle_targeting_input()` when in that state.

**New state:** Add `GameStates.INVENTORY = 5` to `config.py`. This follows the same pattern exactly.

```python
# config.py
class GameStates(Enum):
    PLAYER_TURN = 1
    ENEMY_TURN = 2
    TARGETING = 3
    WORLD_MAP = 4
    INVENTORY = 5  # NEW
```

**State transitions:**
```
PLAYER_TURN
    │ player presses 'i' (or selects "Items" action)
    ▼
INVENTORY
    │ player presses ESC or 'i' again
    ▼
PLAYER_TURN  (no turn consumed — opening inventory is free)

INVENTORY
    │ player selects "Use" consumable
    ▼
PLAYER_TURN (turn consumed — using an item costs a turn)

INVENTORY
    │ player selects "Equip" / "Unequip"
    ▼
PLAYER_TURN (turn consumed — equipping costs a turn)

INVENTORY
    │ player selects "Drop"
    ▼
PLAYER_TURN (turn consumed — dropping costs a turn)
```

**Input routing in `Game.get_event()`:**
```python
def get_event(self, event):
    if self.turn_system.current_state == GameStates.TARGETING:
        self.handle_targeting_input(event)
    elif self.turn_system.current_state == GameStates.INVENTORY:
        self.handle_inventory_input(event)   # NEW
    elif self.turn_system.is_player_turn():
        self.handle_player_input(event)
```

**Inventory screen rendering:**
- Add `InventoryScreen` class (or render method on an `InventorySystem`) — draws a full-screen or overlay panel listing inventory contents.
- Called from `Game.draw()` when `turn_system.current_state == GameStates.INVENTORY`.
- Reads `Inventory.items`, queries `Name` and `Equippable`/`Consumable` on each item entity.

**"Items" action already stubbed:** `party_service.py` already adds `Action(name="Items")` to the player's `ActionList`. The handler in `Game.handle_player_input()` needs to be wired to set `turn_system.current_state = GameStates.INVENTORY`.

---

## New Systems Required

| System | File | Registration | Purpose |
|--------|------|--------------|---------|
| `EquipmentSystem` | `ecs/systems/equipment_system.py` | `esper.add_processor()` before `CombatSystem` | Computes `EffectiveStats` from `Stats` + equipped items each frame |
| `PickupSystem` | `ecs/systems/pickup_system.py` | `esper.add_processor()` | Handles `PickupRequest` component → moves item from ground to inventory |
| `LootSystem` | `ecs/systems/loot_system.py` | `esper.add_processor()` | Listens for `entity_died`, spawns loot from `LootTable` |
| `ItemActionSystem` | `ecs/systems/item_action_system.py` | explicit call, like `ActionSystem` | Handles use/equip/unequip/drop requests from inventory UI |

**Alternatively:** `PickupSystem` and `ItemActionSystem` can be unified into a single `ItemSystem` that handles all item interactions. The separation is cleaner for testing but adds files. Unify for the first milestone, split later if complexity warrants.

---

## Data Flow

### Pick-Up Flow

```
Player moves onto item tile
    │
    ▼
MovementSystem.process()
    moves player to (x, y)
    detects item entity at (x, y) — no Blocker, so no attack
    │
    ▼
(After move: player and item are at same position)
    │
    ▼ player presses 'g' (or "Get" triggers automatically)
Game.handle_player_input()
    esper.add_component(player, PickupRequest())
    │
    ▼
PickupSystem.process()
    for ent, (pos, req) in get_components(Position, PickupRequest):
        find item at (pos.x, pos.y, pos.layer) with Portable
        if found:
            esper.remove_component(item, Position)
            esper.remove_component(item, Renderable)
            esper.add_component(item, Contained(owner=ent, slot="pack"))
            inv = esper.component_for_entity(ent, Inventory)
            inv.items.append(item_eid)
            esper.dispatch_event("log_message", f"You pick up the {item_name}.")
        esper.remove_component(ent, PickupRequest)
    turn_system.end_player_turn()
```

### Equipment Flow

```
Player in INVENTORY state, selects item, presses 'e'
    │
    ▼
handle_inventory_input()
    esper.add_component(player, EquipRequest(item_eid=selected_item))
    │
    ▼
ItemSystem.process()
    for ent, req in get_component(EquipRequest):
        item = req.item_eid
        equippable = esper.component_for_entity(item, Equippable)
        slot = equippable.slot
        # Unequip existing item in same slot
        for other_item_eid in esper.component_for_entity(ent, Inventory).items:
            other_contained = esper.try_component(other_item_eid, Contained)
            if other_contained and other_contained.slot == slot:
                other_contained.slot = "pack"
        # Equip new item
        contained = esper.component_for_entity(item, Contained)
        contained.slot = slot
        esper.remove_component(ent, EquipRequest)
    # EffectiveStats updated next frame by EquipmentSystem
```

### Loot Drop Flow

```
CombatSystem → target HP <= 0 → dispatch "entity_died"
    │
    ▼
DeathSystem.on_entity_died()    [existing — unchanged]
    transforms entity to corpse
    │
    ▼
LootSystem.on_entity_died()     [NEW — also registered for "entity_died"]
    reads LootTable on entity
    for each entry: roll chance → ItemFactory.create_on_ground()
```

Both `DeathSystem` and `LootSystem` register handlers for `"entity_died"`. Esper dispatches to all registered handlers. Order of handler execution follows registration order — `DeathSystem` runs first (registered in `Game.startup()` first), `LootSystem` second. This is correct: corpse transformation happens before loot spawning, which is the logical order.

---

## Integration Points

### New Files

| File | Purpose |
|------|---------|
| `entities/item_registry.py` | `ItemTemplate` dataclass + `ItemRegistry` singleton |
| `entities/item_factory.py` | `ItemFactory.create_on_ground()`, `ItemFactory.create_in_inventory()` |
| `ecs/systems/equipment_system.py` | `EquipmentSystem` — computes `EffectiveStats` each frame |
| `ecs/systems/pickup_system.py` | `PickupSystem` — handles `PickupRequest` → inventory transfer |
| `ecs/systems/loot_system.py` | `LootSystem` — listens to `entity_died`, spawns loot |
| `ecs/systems/item_action_system.py` | `ItemActionSystem` — handles use/equip/drop from inventory UI |
| `assets/data/items.json` | Item template data (sprites, bonuses, effects) |

### Modified Files

| File | Change | Scope |
|------|--------|-------|
| `ecs/components.py` | Add: `Portable`, `Contained`, `Equippable`, `Consumable`, `ItemMaterial`, `EffectiveStats`, `LootTable`, `PickupRequest`, `EquipRequest`. Tighten `Inventory.items: List[int]`. | ~60 lines added |
| `config.py` | Add `GameStates.INVENTORY = 5` | 1 line |
| `entities/entity_registry.py` | Add `loot_table: List[dict]` field to `EntityTemplate` with `field(default_factory=list)` | 1 line |
| `entities/entity_factory.py` | Add `if template.loot_table: components.append(LootTable(...))` | 3 lines |
| `services/resource_loader.py` | Add `ResourceLoader.load_items(filepath)` static method | ~60 lines |
| `game_states.py` | Add `INVENTORY` state routing, wire new systems, extend `_collect_carried_items()` into `transition_map()`, wire "Items" action handler | ~40 lines |
| `ecs/systems/combat_system.py` | Change `attacker_stats.power` and `target_stats.defense` to use `_get_power()` / `_get_defense()` helpers that prefer `EffectiveStats` | ~10 lines |
| `main.py` | Add `ResourceLoader.load_items("assets/data/items.json")` call | 1 line |

### Unchanged Files

| File | Reason |
|------|--------|
| `map/map_container.py` | `freeze()`/`thaw()` unchanged. Exclusion list is computed by caller. |
| `ecs/systems/death_system.py` | Unchanged. `LootSystem` is a separate handler on the same event. |
| `ecs/systems/movement_system.py` | Items have no `Blocker` — MovementSystem is unaware of them. |
| `ecs/systems/render_system.py` | Items on ground are rendered automatically via `(Position, Renderable)` query — no changes needed. |
| `ecs/systems/action_system.py` | Inspect mode already shows entities with `Name` at target tile — items on ground are described for free. |
| `ecs/systems/ai_system.py` | AI does not interact with items in this milestone. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `EquipmentSystem` → `CombatSystem` | `EffectiveStats` component (written by Equipment, read by Combat) | Run order matters: Equipment before Combat |
| `LootSystem` ↔ `DeathSystem` | Both listen to `"entity_died"` esper event | Registration order determines call order |
| `PickupSystem` → `Inventory` | Directly mutates `Inventory.items` list and `Contained` component | System owns the pick-up transaction |
| `ItemFactory` → `ItemRegistry` | Direct call: `ItemRegistry.get(template_id)` | Same pattern as `EntityFactory` → `EntityRegistry` |
| `Game.transition_map()` → `MapContainer.freeze()` | Caller computes exclusion list including carried items | No inventory logic in map container |
| Inventory UI → `Inventory` component | Reads `Inventory.items`, queries `Name`/`Equippable`/`Consumable` per item | UI is read-only; mutations go via request components |

---

## Recommended Build Order

Dependencies drive this order. Each step is independently testable before the next begins.

**Step 1 — Components (foundation, zero deps):**
Add all new components to `ecs/components.py`: `Portable`, `Contained`, `Equippable`, `Consumable`, `ItemMaterial`, `EffectiveStats`, `LootTable`, `PickupRequest`, `EquipRequest`. Tighten `Inventory` type annotation.
- Test: `from ecs.components import Portable, Contained, ...` imports without error.

**Step 2 — ItemRegistry + ItemTemplate (no game deps):**
Create `entities/item_registry.py` with `ItemTemplate` and `ItemRegistry`. Write `ResourceLoader.load_items()`. Create `assets/data/items.json` with 2-3 test items.
- Test: Load JSON, verify `ItemRegistry.get("iron_sword")` returns correct template.

**Step 3 — ItemFactory (depends on Steps 1+2):**
Create `entities/item_factory.py` with `create_on_ground()` and `create_in_inventory()`.
- Test: Create item in world, verify `(Position, Renderable, Portable)` are present for ground item.

**Step 4 — EquipmentSystem + CombatSystem change (depends on Step 1):**
Create `EquipmentSystem`. Modify `CombatSystem` to use `_get_power()` / `_get_defense()` helpers.
Register `EquipmentSystem` before `CombatSystem` in `game_states.py`.
- Test: Entity with no equipment gets `EffectiveStats` equal to base `Stats`. Entity with equipped sword gets `EffectiveStats.power = base + bonus`.

**Step 5 — LootTable → EntityTemplate + EntityFactory + LootSystem (depends on Steps 1+3):**
Add `loot_table` field to `EntityTemplate`. Extend `EntityFactory` to attach `LootTable`. Create `LootSystem`. Update `entities.json` orc with a test loot entry.
- Test: Kill orc, verify item entity appears at orc's position.

**Step 6 — PickupSystem (depends on Steps 1+3):**
Create `PickupSystem`. Add `PickupRequest` handling. Wire player `'g'` key in `Game.handle_player_input()`.
- Test: Item on ground, player walks onto it and presses 'g', item moves from ground to `Inventory.items`.

**Step 7 — freeze/thaw exclusion fix (depends on Step 6):**
Add `_collect_carried_items()` to `Game`. Modify `transition_map()` to pass full exclusion list to `freeze()`.
- Test: Player picks up item, transitions map, transitions back — item still in inventory.

**Step 8 — Inventory UI + INVENTORY game state (depends on Steps 1+6):**
Add `GameStates.INVENTORY = 5`. Add input routing in `get_event()`. Add `handle_inventory_input()`. Create inventory rendering (draw panel with item list). Wire "Items" action handler.
- Test: Press 'i' — inventory screen appears. ESC returns to game. Items listed correctly.

**Step 9 — ItemActionSystem: equip/unequip/use/drop (depends on Steps 1+4+6+8):**
Create `ItemActionSystem`. Wire equip/unequip, use (consumable), drop from inventory UI.
- Test: Equip sword — `EffectiveStats.power` increases. Use potion — HP increases, potion removed from inventory. Drop item — item appears on ground at player position.

---

## Anti-Patterns

### Anti-Pattern 1: Modifying Base Stats on Equip

**What people do:** `stats.defense += equippable.bonus_defense` when equipping.
**Why it's wrong:** Unequipping requires `stats.defense -= equippable.bonus_defense`. If the item is ever destroyed, dropped, or the player crashes, the base stat is permanently corrupted. Stacking multiple items compounds the error.
**Do this instead:** Keep `Stats` as immutable base values. `EquipmentSystem` computes `EffectiveStats` from scratch each frame. `CombatSystem` reads `EffectiveStats`.

### Anti-Pattern 2: Storing Item Entity IDs in Position

**What people do:** Add a `List[int]` field to `Position` for "items at this location" so the pickup system can find them.
**Why it's wrong:** Every `Position` component now maintains a list that must be kept in sync with item entity positions. Whenever an item is moved, the old tile's list must be updated and the new tile's list too. This is a spatial index — esper already handles this via component queries.
**Do this instead:** `PickupSystem` queries `(Position, Portable)` and filters by `(pos.x == player.x and pos.y == player.y)`. No auxiliary data structure needed.

### Anti-Pattern 3: Keeping Position on Carried Items (with InInventory Tag)

**What people do:** Add an `InInventory` tag component to carried items and keep `Position` set to the owner's position, thinking it makes item location queries simpler.
**Why it's wrong:** Every system that queries `(Position, X)` now iterates over carried items too. `MovementSystem`, `RenderSystem`, `VisibilitySystem` all get false hits. Every system needs to check for `InInventory` to skip these entities.
**Do this instead:** Remove `Position` from carried items. The `Contained` component is the location signal for carried items. Systems that care about items-on-ground query `(Position, Portable)`. Systems that care about inventory contents query `(Contained, ...)`.

### Anti-Pattern 4: Putting Loot Drop Logic in DeathSystem

**What people do:** Add loot spawning code directly inside `DeathSystem.on_entity_died()`.
**Why it's wrong:** `DeathSystem` is responsible for entity transformation (corpse state). Mixing loot spawning creates a system with two responsibilities. Testing becomes harder: you cannot test loot drops independently of death transformation. Future changes to either concern require modifying the same function.
**Do this instead:** `LootSystem` registers its own handler for `"entity_died"`. It runs after `DeathSystem` because it is registered later. Both are self-contained.

### Anti-Pattern 5: Freezing Without Excluding Carried Items

**What people do:** Call `map_container.freeze(world, exclude_entities=[player_entity])` without accounting for item entities in the player's inventory.
**Why it's wrong:** Carried item entities have no `Position` but exist in the esper world. `freeze()` iterates `world._entities` and deletes everything not in `exclude_entities`. Carried items are deleted. The player's `Inventory.items` list now contains stale entity IDs pointing to deleted entities. Accessing them in any system raises `KeyError`.
**Do this instead:** Before calling `freeze()`, collect all entity IDs in the player's `Inventory.items` and add them to the exclusion list.

---

## Sources

- Direct codebase analysis: `ecs/components.py` — existing `Inventory`, `Stats`, `Position`, `Renderable` structures
- Direct codebase analysis: `entities/entity_registry.py` — `EntityTemplate` flyweight pattern
- Direct codebase analysis: `entities/entity_factory.py` — conditional component attachment pattern
- Direct codebase analysis: `services/resource_loader.py` — JSON loading pattern for `load_entities()`
- Direct codebase analysis: `ecs/systems/death_system.py` — `esper.set_handler("entity_died", ...)` event pattern
- Direct codebase analysis: `ecs/systems/combat_system.py` — `Stats` usage, `AttackIntent` pattern
- Direct codebase analysis: `map/map_container.py` — `freeze()`/`thaw()` implementation, `exclude_entities` parameter
- Direct codebase analysis: `game_states.py` — `GameStates` enum, `transition_map()`, `TARGETING` state routing
- Direct codebase analysis: `config.py` — `SpriteLayer.ITEMS = 3` (already defined), `GameStates` enum
- Direct codebase analysis: `services/party_service.py` — `Inventory()` component already on player, `Action(name="Items")` already in `ActionList`

---
*Architecture research for: Roguelike RPG — Item & Inventory System Integration with Existing ECS*
*Researched: 2026-02-15*
