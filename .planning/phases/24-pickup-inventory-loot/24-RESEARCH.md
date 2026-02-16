# Phase 24: Pickup, Inventory Screen, and Loot Drops - Research

**Researched:** 2026-02-16
**Domain:** Inventory management, UI States, Loot systems
**Confidence:** HIGH

## Summary

This phase implements the player's ability to interact with items in the world. Key components are the pickup/drop logic, a modal inventory UI, and a death-triggered loot system. We will leverage the existing `GameStates` enum and `GameState` architecture to handle the inventory screen as a separate modal state. The loot system will be integrated into the `DeathSystem` via the `entity_died` event.

**Primary recommendation:** Use a dedicated `InventoryState` class in `game_states.py` to handle the inventory UI. Implement pickup/drop as simple logic in `Game.handle_player_input` or a helper service. For loot drops, add a `LootTable` component to monsters and handle it in `DeathSystem.on_entity_died`.

## User Constraints (from ROADMAP.md)

### Locked Decisions
- Pressing `G` picks up an item at the player's position.
- Pickup is rejected if weight exceeds capacity.
- Pressing `I` opens the modal inventory screen (`GameStates.INVENTORY`).
- Inventory screen uses arrow keys for navigation.
- Pressing `D` from the inventory screen drops the selected item.
- Monsters produce contextual loot on death (e.g., wolf drops pelt).
- Loot spawns on or adjacent to death tile, scattering if occupied.

### Claude's Discretion
- Visual design of the inventory list.
- Implementation of weight capacity (where to store the limit).
- Exact format of loot tables.
- Scattering algorithm details.

## Architecture Patterns

### Pattern 1: Modal State Transition
**What:** Using `GameStates.INVENTORY` to pause the main game loop's input handling and redirect it to a dedicated UI state.
**Why:** Keeps the input handling clean and prevents player movement while in menus.

### Pattern 2: Event-Driven Loot
**What:** Listening for `entity_died` in `DeathSystem` and checking for a `LootTable` component.
**Why:** Decouples combat logic from item generation.

### Pattern 3: Spatial Scattering
**What:** If an item cannot be dropped on a tile (e.g., wall or too many items, though we don't have a per-tile item limit yet), find the nearest walkable tile.
**Logic:**
1. Check death tile.
2. If blocked, check 8 neighbors.
3. If all 8 neighbors are blocked, don't drop (or drop on death tile anyway as a fallback).

## Common Pitfalls

### Pitfall 1: Capacity Calculation
**What goes wrong:** Calculating total weight every frame can be slow if inventories are huge.
**How to avoid:** Recalculate only when items are added/removed, or just calculate on-demand during pickup (inventories are likely small enough for this not to matter).

### Pitfall 2: Modal State Persistence
**What goes wrong:** Losing the main game state when entering inventory.
**How to avoid:** Use the `persist` dictionary to share state (camera, world, player_entity) between `Game` and `InventoryState`.

### Pitfall 3: Input Leakage
**What goes wrong:** Pressing 'I' toggles inventory on, but 'I' also triggers an action in the game world.
**How to avoid:** Ensure the `GameState` manager correctly consumes events and doesn't pass them to the previous state.

## Proposed Components

### `LootTable`
```python
@dataclass
class LootTable:
    entries: List[Dict] # e.g., [{"item_id": "wolf_pelt", "chance": 1.0}]
```

## Proposed Loot Logic (in DeathSystem)
```python
def on_entity_died(self, entity):
    # ... existing corpse logic ...
    
    if self.world.has_component(entity, LootTable):
        loot = self.world.component_for_entity(entity, LootTable)
        pos = self.world.component_for_entity(entity, Position)
        
        for entry in loot.entries:
            if random.random() <= entry["chance"]:
                drop_pos = find_scatter_pos(self.world, pos.x, pos.y, pos.layer)
                ItemFactory.create_on_ground(self.world, entry["item_id"], *drop_pos)
```

## Sources
- `game_states.py`: Existing `TitleScreen` and `Game` states.
- `ecs/systems/death_system.py`: Target for loot logic.
- `REQUIREMENTS.md`: Detailed requirements for INV-01 to INV-05.
