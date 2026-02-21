# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A roguelike RPG/simulation built with **Python**, **Pygame**, and **esper** (ECS framework). The game features a tile-based world with ASCII rendering, day/night cycles, NPC schedules, multi-layer maps with portals, FOV/shadowcasting visibility, A* pathfinding, and a turn-based combat system.

## Tech Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python 3.10+                        |
| Rendering       | Pygame (ASCII glyphs on tile grid)  |
| ECS Framework   | esper 3.x (module-level API)        |
| Pathfinding     | `pathfinding` library (A*, no diagonals) |
| Data Format     | JSON for all game content           |

## Running the Project

```bash
pip install pygame esper pathfinding
python main.py
```

## Testing

Tests live in `tests/` and are named `verify_*.py`:

```bash
# Run all tests
python -m pytest tests/ -v

# Run a single test
python -m pytest tests/verify_ai_system.py -v
```

Between tests, always call `reset_world()` to clear ECS state, and `TileRegistry.clear()` / `EntityRegistry.clear()` / etc. to clear registries.

## Planning

Development plans live in `.planning/`. Phase-based roadmap is in `.planning/phases/` (numbered `01-` through `35+`). Quick-fix and tech-debt docs live in `.planning/quick/`. These are the source of truth for roadmap items and feature specs.

## Architecture

### ECS (Entity Component System) — esper 3.x

esper 3.x operates at module level (no `World` instance). All ECS calls go through the `esper` module directly:

```python
import esper

entity = esper.create_entity(Position(x, y), Renderable("@", 5))

for ent, (pos, rend) in esper.get_components(Position, Renderable):
    ...

esper.dispatch_event("log_message", "Hello!")
esper.set_handler("entity_died", handler_func)
```

**`ecs/world.py`** provides `get_world()` which returns the `esper` module itself — this is a compatibility shim, not a world instance.

### Core Patterns

- **Registry/Flyweight Pattern**: Shared immutable templates loaded from JSON → `TileRegistry`, `EntityRegistry`, `ItemRegistry`, `ScheduleRegistry`
- **Factory Pattern**: `EntityFactory`, `ItemFactory` create ECS entities from registry templates
- **Data-Driven Design**: All game content (tiles, entities, items, schedules, prefabs) defined in `assets/data/*.json`
- **Service Layer**: Stateless or singleton services (`VisibilityService`, `PathfindingService`, `RenderService`, `WorldClockService`, etc.)
- **State Machine**: `GameController` → `GameState` subclasses (`TitleScreen`, `Game`, `WorldMapState`)

### Processing Order (ECS Processors)

```
TurnSystem → EquipmentSystem → VisibilitySystem → MovementSystem → CombatSystem → DeathSystem → FCTSystem
```

Additionally called manually per frame (not registered as processors):
- `ScheduleSystem.process()` — before AI, during enemy turn
- `AISystem.process()` — during enemy turn
- `RenderSystem.process()` — during draw
- `UISystem.process()` — during draw

### Turn Flow

```
PLAYER_TURN → (player input) → end_player_turn() → ENEMY_TURN
ENEMY_TURN  → ScheduleSystem → AISystem → end_enemy_turn() → PLAYER_TURN
```

World clock advances 1 tick per player turn. 1 hour = 60 ticks.

## Project Structure

```
.
├── main.py                          # Entry point, GameController
├── config.py                        # Constants, enums (SpriteLayer, GameStates, colors)
├── game_states.py                   # State machine (TitleScreen, Game, WorldMapState)
│
├── assets/data/
│   ├── tile_types.json              # Tile definitions
│   ├── entities.json                # NPC/monster templates
│   ├── items.json                   # Item templates
│   ├── schedules.json               # NPC daily routines
│   └── prefabs/                     # Prefab room layouts
│
├── ecs/
│   ├── world.py                     # get_world() / reset_world() shims
│   ├── components.py                # All dataclass components
│   └── systems/                     # One file per system (see Processing Order above)
│
├── entities/
│   ├── entity_factory.py / entity_registry.py
│   ├── item_factory.py / item_registry.py
│   └── schedule_registry.py
│
├── map/
│   ├── tile.py / tile_registry.py   # Tile class, TileType flyweight
│   ├── map_layer.py                 # MapLayer (2D tile grid)
│   └── map_container.py            # MapContainer (layers + freeze/thaw)
│
├── services/                        # Stateless services + InputManager
├── components/
│   └── camera.py                    # Camera with tile ↔ screen coordinate conversion
└── ui/
    ├── message_log.py               # Rich text [color=x] message log
    ├── stack_manager.py             # UIStack for modal windows
    └── windows/                     # inventory.py, character.py, tooltip.py
```

## Key Components Reference

### Components (`ecs/components.py`)

| Component         | Purpose                                      |
|-------------------|----------------------------------------------|
| `PlayerTag`       | Marker for the player entity                 |
| `AI`              | Marker for AI-controlled entities            |
| `Blocker`         | Marker for movement-blocking entities        |
| `Position`        | x, y, layer (map layer index)               |
| `Renderable`      | sprite char, SpriteLayer value, color        |
| `Name`            | Entity display name                          |
| `Description`     | Entity description; optional wounded variant |
| `Stats`           | Base stats + `base_*` fields for equipment   |
| `EffectiveStats`  | Computed stats (base + equipment + modifiers)|
| `StatModifiers`   | Additive stat modifiers (equipment/buffs)    |
| `AIBehaviorState` | Current `AIState` + `Alignment`              |
| `Activity`        | Schedule-driven activity + target position   |
| `Schedule`        | Links entity to a `schedule_id`              |
| `PathData`        | A* path + destination for NPC movement       |
| `ChaseData`       | Chase state: last known player pos, timeout  |
| `WanderData`      | Stub component for wander state              |
| `TurnOrder`       | Priority ordering for turn processing        |
| `Portal`          | Map transition target                        |
| `LootTable`       | Death loot drops [(template_id, chance)]     |
| `Inventory`       | List of item entity IDs                      |
| `Equipment`       | Slot → entity_id mapping                     |
| `Equippable`      | Declares which `SlotType` this item occupies |
| `Portable`        | Weight value for inventory items             |
| `ItemMaterial`    | Material type (iron, wood, glass, etc.)      |
| `Consumable`      | Use effect (heal_hp, etc.)                   |
| `LightSource`     | Light emission radius                        |
| `ActionList`      | Available actions with selected index        |
| `HotbarSlots`     | Hotbar slot mapping (slots 1–9)              |
| `Targeting`       | Targeting state: origin, target, range, mode |
| `FCT`             | Floating combat text with velocity + TTL     |

### Enums

**`config.py`:**
- **`SpriteLayer`**: GROUND(0) → DECOR_BOTTOM(1) → TRAPS(2) → ITEMS(3) → CORPSES(4) → ENTITIES(5) → DECOR_TOP(6) → EFFECTS(7)
- **`GameStates`**: PLAYER_TURN, ENEMY_TURN, TARGETING, WORLD_MAP, INVENTORY, MENU, EXAMINE
- **`LogCategory`**: DAMAGE_DEALT, DAMAGE_RECEIVED, HEALING, LOOT, SYSTEM, ALERT

**`ecs/components.py`:**
- **`AIState`**: IDLE, WANDER, CHASE, TALK, WORK, PATROL, SOCIALIZE, SLEEP
- **`Alignment`**: HOSTILE, NEUTRAL, FRIENDLY
- **`SlotType`**: HEAD, BODY, MAIN_HAND, OFF_HAND, FEET, ACCESSORY

**`map/tile.py`:**
- **`VisibilityState`**: UNEXPLORED, VISIBLE, SHROUDED, FORGOTTEN

**`services/input_manager.py`:**
- **`InputCommand`**: Full enum of 40+ mapped player actions (movement, interact, UI, debug, etc.)

## Conventions & Rules

### Code Style
- Dataclass components, no inheritance on components
- Type hints on function signatures
- Docstrings on public methods (Google style or descriptive)
- Constants in `config.py`, prefixed with `UI_`, `DEBUG_`, `DN_`, `COLOR_`
- Comment tags for traceability: `AISYS-01`, `WNDR-04`, `CHAS-03`, etc.

### ECS Rules
- **Never store `World` instances** — use `esper` module directly or `get_world()`
- **Components are plain dataclasses** — no methods with side effects
- **Systems do not hold entity references** — query via `esper.get_components()` each frame
- **Events for cross-system communication**: `esper.dispatch_event()` / `esper.set_handler()`
- **Use `list()` wrapper** on `esper.get_components()` when modifying entities during iteration
- **EffectiveStats** is the read source for combat/display; **Stats** is the write target for HP/mana changes
- When adding new components: add to `ecs/components.py`, update `DeathSystem` cleanup list if relevant

### Map System Rules
- Maps are `MapContainer` with multiple `MapLayer`s (vertical layers, not separate maps)
- `freeze()` / `thaw()` serializes entities when switching maps — player party excluded via `get_entity_closure()`
- Tile types come from `TileRegistry` — use `Tile(type_id="floor_stone")`, never hardcode tile properties
- Prefabs are JSON files stamped onto existing layers via `MapService.load_prefab()`

### Data-Driven Content
- **Add new tiles**: `assets/data/tile_types.json` → automatically available via `TileRegistry`
- **Add new entities**: `assets/data/entities.json` → spawn with `EntityFactory.create(world, "id", x, y)`
- **Add new items**: `assets/data/items.json` → create with `ItemFactory.create(world, "id")`
- **Add new schedules**: `assets/data/schedules.json` → assign via `schedule_id` in entity template
- **Sprite layers in JSON** use string keys matching `SpriteLayer` enum names (e.g., `"GROUND"`, `"ITEMS"`)

### AI Behavior
- Hostile NPCs detect player via shadowcasting FOV → transition to CHASE
- CHASE uses A* pathfinding with greedy Manhattan fallback
- NPCs lose chase after `LOSE_SIGHT_TURNS` (3) without line of sight
- Scheduled NPCs follow `PathData` priority unless in CHASE state
- Sleeping NPCs skip all behavior; woken by bump or combat

### Input Handling
- `InputManager` maps `pygame.KEYDOWN` → `InputCommand` enum, context-aware by `GameStates`
- `UIStack` modal windows consume events before game input
- Movement keys: Arrow keys (WASD used for action selection / targeting)

## Debug Controls

| Key | Action |
|-----|--------|
| F3  | Toggle debug master |
| F4  | Toggle player FOV overlay |
| F5  | Toggle NPC FOV overlay |
| F6  | Toggle chase target lines |
| F7  | Toggle AI state labels |

## Common Pitfalls

1. **esper 3.x has no World class** — `esper` is the world. Don't try to instantiate `esper.World()`.
2. **`Stats` vs `EffectiveStats`** — Always read from `EffectiveStats` (or fall back to `Stats`). Write HP/mana changes to `Stats`. `EquipmentSystem` recomputes `EffectiveStats` each frame.
3. **Map freeze/thaw** — Entities not in `exclude_entities` get serialized into `MapContainer.frozen_entities` and deleted from esper. Always exclude the player party.
4. **Tile `walkable` property** — Registry-backed tiles use `_walkable` from `TileType`. Legacy tiles derive from sprite character. Don't set `walkable` directly.
5. **`SpriteLayer` in JSON** — Use the enum name string (e.g., `"ENTITIES"`), converted to enum at factory time.
6. **Event handlers** — `esper.set_handler()` persists across `clear_database()` only if `event_registry` isn't cleared. `reset_world()` clears both.
