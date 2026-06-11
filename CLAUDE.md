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

State cleanup between tests is automatic: the autouse fixture in `tests/conftest.py` calls `reset_world()` and `default_content.clear_all()` before every test. Tests load the JSON content they need themselves.

## Planning

The project direction and phase plan live in `ROADMAP.md` (source of truth
for upcoming features). The development history through v1.6 is preserved in
`DEV_JOURNAL.md`. The former `.planning/` directory has been retired.

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

**`core/ecs.py`** provides `reset_world()` for clearing ECS state (used by tests). The former `get_world()` shim has been removed — always `import esper` directly.

### Core Patterns

- **Registry/Flyweight Pattern**: Shared immutable templates loaded from JSON → instance-based registries (`tile_registry`, `entity_registry`, `item_registry`, `schedule_registry`) bundled in the `ContentDatabase` facade (`game/content/content_database.py`)
- **Factory Pattern**: `EntityFactory`, `ItemFactory` create ECS entities from registry templates
- **Data-Driven Design**: All game content (tiles, entities, items, schedules, prefabs) defined in `assets/data/*.json`
- **Service Layer**: Stateless or singleton services (`VisibilityService`, `PathfindingService`, `RenderService`, `WorldClockService`, etc.)
- **State Machine**: `GameController` → `GameState` subclasses (`TitleScreen`, `GameplayState`, `WorldMapState`, `GameOver`); states are thin and delegate to `InputController` / `TurnOrchestrator` / `RenderPipeline`

### System Categories

The ECS logic is separated into four distinct categories:

1. **FRAME-PROCESSORS**: Registered once with `esper.add_processor()` (via `register_processors()` in the bootstrap) and run every frame by `TurnOrchestrator.update()` via `esper.process()`.
   - `TurnSystem`, `EquipmentSystem`, `VisibilitySystem`, `MovementSystem`, `CombatSystem`, `FCTSystem`
2. **PHASE-SYSTEMS**: Called by `TurnOrchestrator` during specific game phases (like enemy turn).
   - `AISystem` (`ENEMY_TURN`), `ScheduleSystem` (`ENEMY_TURN`)
3. **RENDER-SYSTEMS**: Called by `RenderPipeline` during the `draw()` cycle. (Re)created in `GameplayState.startup()`.
   - `RenderSystem`, `UISystem`, `DebugRenderSystem`
4. **EVENT-SYSTEMS**: React exclusively to events (callbacks set up in `__init__` via `esper.set_handler()`), without a `process()` loop and therefore *not* added as an `esper.Processor`.
   - `DeathSystem` (`entity_died` event)

### Turn Flow

```
PLAYER_TURN → (player input) → end_player_turn() → ENEMY_TURN
ENEMY_TURN  → ScheduleSystem → AISystem → end_enemy_turn() → PLAYER_TURN
```

World clock advances 1 tick per player turn. 1 hour = 60 ticks.

### Event Policy — "Befehle nach unten, Fakten nach oben"

**Direct call** when the caller needs a result or must guarantee ordering:
`action_system.perform_action(...)`, `turn_system.end_player_turn()`,
`schedule_system.process(...)` — anything a controller/orchestrator drives.

**Event (`esper.dispatch_event`)** when something *happened* and any number of
observers may react. Events carry past-tense names: `entity_died`,
`player_died`, `log_message` (a fact being reported).

**Request events** (`*_requested`) are the one sanctioned exception: a lower
layer asks the orchestration layer to do something it must not know about
directly (e.g. `map_change_requested` dispatched by ActionSystem, handled by
MapTransitionService). Use sparingly — never as a substitute for a direct call
within the same layer.

Whoever dispatches an event must not rely on a handler being registered.

## Project Structure

**Layering rule (machine-checked by `tests/verify_layering.py`):**
`core/` is game-agnostic and must NEVER import from `game/`, `bootstrap`,
`game_context` or `main`. `game/` may use everything in `core/`. `config/`
is neutral constants, usable by both.

```
.
├── main.py                          # Entry point: GameController + main loop only
├── bootstrap.py                     # Composition root: builds the GameContext exactly once
├── game_context.py                  # GameContext / Systems / DebugFlags dataclasses
│
├── config/                          # Constants & enums (neutral, no game imports)
│   ├── __init__.py                  # Re-exports everything for backwards compat
│   ├── game.py                      # SCREEN_*, TILE_SIZE, TICKS_PER_HOUR, DN_SETTINGS
│   ├── ui.py                        # UI_*, HEADER_HEIGHT, LOG_HEIGHT, UI_MODAL_RECT
│   ├── colors.py                    # COLOR_*, UI_COLOR_*
│   ├── debug.py                     # DEBUG_*
│   └── enums.py                     # SpriteLayer, GameStates, LogCategory, LOG_COLORS
│
├── assets/data/
│   ├── tile_types.json              # Tile definitions
│   ├── entities.json                # NPC/monster templates
│   ├── items.json                   # Item templates
│   ├── player.json                  # Player base stats & actions
│   ├── world.json                   # World graph: locations + travel routes
│   ├── schedules.json               # NPC daily routines
│   ├── dialogues.json               # NPC dialogue lines by template_id
│   ├── prefabs/                     # Prefab room layouts
│   └── scenarios/                   # Data-driven map scenarios (e.g. village.json)
│
├── core/                            # GAME-AGNOSTIC layer (never imports game/)
│   ├── ecs.py                       # reset_world() helper (tests)
│   ├── registry.py                  # Generic Registry[T] base class
│   ├── camera.py                    # Camera with tile ↔ screen coordinate conversion
│   ├── input_manager.py             # InputManager + InputCommand enum
│   ├── visibility_service.py        # Shadowcasting FOV
│   ├── world_clock_service.py       # Day/night cycle, time tracking
│   └── ui/
│       ├── stack_manager.py         # UIStack for modal windows
│       ├── message_log.py           # Rich text [color=x] message log
│       └── window_base.py           # UIWindow base class
│
└── game/                            # GAME layer (may use core/)
    ├── components.py                # All dataclass components
    ├── systems/                     # One file per ECS system
    │   ├── map_aware_system.py      # MapAwareSystem mixin (see below)
    │   ├── turn_system.py           # TurnSystem (frame processor)
    │   ├── visibility_system.py     # VisibilitySystem (frame processor)
    │   ├── movement_system.py       # MovementSystem (frame processor)
    │   ├── combat_system.py         # CombatSystem (frame processor)
    │   ├── equipment_system.py      # EquipmentSystem (frame processor)
    │   ├── fct_system.py            # FCTSystem (frame processor)
    │   ├── action_system.py         # ActionSystem (action dispatch)
    │   ├── ai_system.py             # AISystem (phase system)
    │   ├── schedule_system.py       # ScheduleSystem (phase system)
    │   ├── death_system.py          # DeathSystem (event system)
    │   ├── render_system.py         # RenderSystem (render system)
    │   ├── ui_system.py             # UISystem (render system)
    │   └── debug_render_system.py   # DebugRenderSystem (render system)
    ├── content/                     # Templates, registries, factories, loaders
    │   ├── content_database.py      # ContentDatabase facade + default_content
    │   ├── resource_loader.py       # JSON data loading orchestration
    │   ├── entity_registry.py       # EntityRegistry + entity_registry default instance
    │   ├── item_registry.py         # ItemRegistry + item_registry default instance
    │   ├── schedule_registry.py     # ScheduleRegistry + schedule_registry default instance
    │   ├── dialogue_service.py      # DialogueService + dialogue_service default instance
    │   ├── entity_factory.py        # Creates ECS entities from registry templates
    │   └── item_factory.py          # Creates item entities from registry templates
    ├── map/
    │   ├── tile.py                  # Tile class, VisibilityState
    │   ├── tile_registry.py         # TileType flyweight + tile_registry default instance
    │   ├── map_layer.py             # MapLayer (2D tile grid)
    │   ├── map_container.py         # MapContainer (layers + freeze/thaw)
    │   └── map_generator_utils.py   # Shared map generation utilities
    ├── services/
    │   ├── system_initializer.py    # build_systems() / register_processors()
    │   ├── player_action_service.py # Player game rules (move, pickup, portal, wait, targeting)
    │   ├── map_service.py           # Map registry + active map management
    │   ├── map_generator.py         # Village scenario, terrain, prefab loading
    │   ├── map_transition_service.py# Map transition (freeze/thaw, set_map fan-out)
    │   ├── world_graph_service.py   # World graph: locations, routes, current location
    │   ├── save_service.py          # Session snapshot save/load (F9/F10)
    │   ├── save_serialization.py    # Generic dataclass/tile JSON (de)serialization
    │   ├── spawn_service.py         # Monster/NPC spawning
    │   ├── party_service.py         # Player party creation
    │   ├── render_service.py        # Map rendering + viewport tint
    │   ├── pathfinding_service.py   # A* pathfinding wrapper
    │   ├── interaction_resolver.py  # Bump interaction resolution
    │   ├── consumable_service.py    # Item consumption logic
    │   └── equipment_service.py     # Equipment slot logic
    ├── controllers/                 # Gameplay orchestration (driven by states)
    │   ├── input_controller.py      # InputCommand → PlayerActionService / UI (esper-free!)
    │   ├── turn_orchestrator.py     # esper.process + enemy-turn phase systems
    │   └── render_pipeline.py       # map → entities → debug → tint → HUD → windows
    ├── states/                      # Thin state machine states
    │   ├── base.py                  # GameState base class
    │   ├── title.py                 # TitleScreen
    │   ├── gameplay.py              # GameplayState (delegates to controllers)
    │   ├── world_map.py             # WorldMapState
    │   └── game_over.py             # GameOver
    └── ui/windows/
        ├── inventory.py             # Inventory window
        ├── character.py             # Character sheet window
        └── tooltip.py               # Examine/tooltip window
```

### GameContext (`game_context.py`)

All long-lived session state lives in the typed `GameContext` dataclass —
there is no string-keyed `persist` dict anymore:

- `ctx.systems` — `Systems` dataclass with named fields for every ECS system
- `ctx.map_container` — property, always the active map from `MapService`
- `ctx.content` — `ContentDatabase` (all template registries)
- `ctx.debug_flags` — `DebugFlags` dataclass (F3-F7 toggles)
- `ctx.player_entity`, `ctx.camera`, `ctx.ui_stack`, `ctx.world_clock`, ...

`bootstrap.build_game_context()` is the only place that constructs services
and systems. States receive the context via `startup(ctx)`.

## Implementing New Features

This is the playbook for ALL new features. Follow the placement rules and
the matching recipe — do not invent new wiring patterns.

### Step 0: Where does the code go?

Answer these questions in order; the first "yes" decides:

1. **Is it pure data** (a new monster, item, tile, schedule, dialogue,
   map layout)? → JSON in `assets/data/` only. No Python change needed.
2. **Is it a game rule or behavior** (combat formula, AI state, new player
   action, item effect)? → `game/` (see recipes below).
3. **Is it a generic mechanism** that would work in any tile-based game
   (a new FOV algorithm, input device support, UI primitive)? → `core/`.
   `core/` must never import from `game/`, `game_context`, `bootstrap` or
   `main` — `tests/verify_layering.py` will fail otherwise.
4. **Is it a constant** (color, size, timing)? → the matching `config/`
   submodule. Never hardcode magic numbers at the use site.

### Step 1: Pick the recipe

#### Recipe A — New content (no code)

Add an entry to the matching JSON file (`entities.json`, `items.json`,
`tile_types.json`, `schedules.json`, `dialogues.json`, `scenarios/*.json`,
`prefabs/`). Sprite layers use enum NAME strings (e.g. `"ENTITIES"`).
Verify with the relevant registry/factory test, e.g.
`python -m pytest tests/verify_entity_factory.py`.

#### Recipe B — New component

1. Add a plain `@dataclass` to `game/components.py` — no methods with side
   effects, no esper calls inside components.
2. If entities holding it can die: add it to the cleanup list in
   `game/systems/death_system.py`.
3. If it must survive map switches: it is serialized automatically by
   freeze/thaw as long as the entity has `MapBound`.

#### Recipe C — New ECS system

1. Decide the category first (see System Categories): frame processor,
   phase system, render system, or event system.
2. Create `game/systems/<name>_system.py`. Query via
   `esper.get_components()` each call — never store entity references.
3. If it needs the current map: inherit `MapAwareSystem`, do NOT take
   `map_container` in the constructor, and add the system to
   `Systems.map_aware()` in `game_context.py`.
4. Wire it: add a named field to the `Systems` dataclass
   (`game_context.py`) and construct it in `build_systems()`
   (`game/services/system_initializer.py`). Frame processors additionally
   go into the ordered list in `register_processors()`. Phase systems are
   called from `TurnOrchestrator`; render systems from `RenderPipeline`;
   event systems register handlers in their `__init__`.
5. Write `tests/verify_<name>_system.py`.

#### Recipe D — New player action (keypress does something)

The chain is always: key → `InputCommand` → `InputController` →
`PlayerActionService` → ECS. Never skip a link.

1. Add an `InputCommand` member + key mapping in `core/input_manager.py`.
2. Add the rule method to `game/services/player_action_service.py`
   (this is where esper access lives; end the turn here if the action
   costs one).
3. Route the command in `game/controllers/input_controller.py` — pure
   translation, ZERO esper imports (this is asserted in review).
4. Add unit tests in `tests/verify_player_action_service.py` (mock the
   systems via the `Systems` dataclass, see existing tests).

#### Recipe E — New service

1. Create it in `game/services/` (stateless where possible). It receives
   what it needs via constructor — usually the `GameContext` (`ctx`).
2. Construct it exactly once: in `bootstrap.build_game_context()` if
   session-wide, or in `GameplayState.startup()` if it needs the player.
   Nothing outside bootstrap/startup constructs services.
3. Use `logging.getLogger(__name__)`, never `print()`.
4. Add `tests/verify_<service_name>.py`.

#### Recipe F — New UI window

1. Subclass `UIWindow` (`core/ui/window_base.py`) in `game/ui/windows/`.
2. Open it via a push in `InputController` using `UI_MODAL_RECT` from
   `config/ui.py` (add a new rect constant there if the size differs).
3. The window consumes events through `UIStack` — no game logic inside
   the window; call services for rules.

#### Recipe G — New game state (screen)

1. Subclass `GameState` in `game/states/`, keep it a thin coordinator
   (target < 150 lines; delegate real work to controllers/services).
2. Register it in the `states` dict in `main.py`.
3. Transition via `self.next_state = "NAME"; self.done = True`.

#### Recipe H — Cross-system communication

Follow the Event Policy (above). Default to a direct call. Dispatch an
event only for facts (`*_died`, `log_message`) or sanctioned requests
(`*_requested`). New event names must be past tense or `*_requested`.

### Step 2: Verify and commit

1. `python -m pytest tests/ -q` must be green — including
   `verify_layering.py` (core/game rule) and `verify_game_loop_smoke.py`
   (the game still boots and plays a full turn headless).
2. New logic gets tests in the same change: unit tests for services,
   `verify_<name>.py` for systems.
3. `ruff check <changed files>` introduces no new findings.
4. One commit per completed task (existing project rule). If the change
   alters architecture or conventions, update CLAUDE.md in the same commit
   — documentation drift is how the last God-class happened.

## Key Components Reference

### Components (`game/components.py`)

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
| `Targeting`       | Targeting state: origin, target, range, mode |
| `FCT`             | Floating combat text with velocity + TTL     |

### Enums

**`config/enums.py`:**
- **`SpriteLayer`**: GROUND(0) → DECOR_BOTTOM(1) → TRAPS(2) → ITEMS(3) → CORPSES(4) → ENTITIES(5) → DECOR_TOP(6) → EFFECTS(7)
- **`GameStates`**: PLAYER_TURN, ENEMY_TURN, TARGETING, WORLD_MAP, INVENTORY, MENU, EXAMINE, GAME_OVER
- **`LogCategory`**: DAMAGE_DEALT, DAMAGE_RECEIVED, HEALING, LOOT, SYSTEM, ALERT

**`game/components.py`:**
- **`AIState`**: IDLE, WANDER, CHASE, TALK, WORK, PATROL, SOCIALIZE, SLEEP
- **`Alignment`**: HOSTILE, NEUTRAL, FRIENDLY
- **`SlotType`**: HEAD, BODY, MAIN_HAND, OFF_HAND, FEET, ACCESSORY

**`game/map/tile.py`:**
- **`VisibilityState`**: UNEXPLORED, VISIBLE, SHROUDED, FORGOTTEN

**`core/input_manager.py`:**
- **`InputCommand`**: Full enum of 40+ mapped player actions (movement, interact, UI, debug, etc.)

### MapAwareSystem Mixin

Systems that need a reference to the current `MapContainer` inherit from `MapAwareSystem` (`game/systems/map_aware_system.py`):

```python
class MapAwareSystem:
    def __init__(self):
        self._map_container = None

    def set_map(self, map_container):
        self._map_container = map_container
```

**Systems using this mixin:** `VisibilitySystem`, `ActionSystem`, `MovementSystem`, `DeathSystem`, `RenderSystem`, `DebugRenderSystem`

**Rule:** Constructors do NOT take `map_container`. Instead, `build_systems()` calls `set_map()` after creation, and `MapTransitionService` re-points all systems from `Systems.map_aware()` on every map transition.

## Conventions & Rules

### AI Assistant Rules
- **Committing:** ALWAYS create a git commit after every completed task (e.g. a `ROADMAP.md` phase task or a `task.md` checklist item). Do not wait until the entire phase is complete to commit.

### Code Style
- Dataclass components, no inheritance on components
- Type hints on function signatures
- Docstrings on public methods (Google style or descriptive)
- Constants in `config/` submodules, prefixed with `UI_`, `DEBUG_`, `DN_`, `COLOR_`
- Comment tags for traceability: `AISYS-01`, `WNDR-04`, `CHAS-03`, etc.
- **Logging:** Use Python `logging` module — `logging.getLogger(__name__)` per module. `main.py` configures `logging.basicConfig()`. No `print()` in production code.

### ECS Rules
- **Never store `World` instances** — use the `esper` module directly
- **Components are plain dataclasses** — no methods with side effects
- **Systems do not hold entity references** — query via `esper.get_components()` each frame
- **Events for cross-system communication**: `esper.dispatch_event()` / `esper.set_handler()`
- **Use `list()` wrapper** on `esper.get_components()` when modifying entities during iteration
- **EffectiveStats** is the read source for combat/display; **Stats** is the write target for HP/mana changes
- When adding new components: add to `game/components.py`, update `DeathSystem` cleanup list if relevant

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
- **Player stats**: `assets/data/player.json` → base stats and actions loaded by `PartyService`
- **Dialogues**: `assets/data/dialogues.json` → NPC dialogue lines keyed by template_id, loaded by `DialogueService`
- **Map scenarios**: `assets/data/scenarios/*.json` → data-driven map layouts loaded by `MapGenerator`
- **Sprite layers in JSON** use string keys matching `SpriteLayer` enum names (e.g., `"GROUND"`, `"ITEMS"`)

### AI Behavior
- Hostile NPCs detect player via shadowcasting FOV → transition to CHASE
- CHASE uses A* pathfinding with greedy Manhattan fallback
- NPCs lose chase after `LOSE_SIGHT_TURNS` (3) without line of sight
- Scheduled NPCs follow `PathData` priority unless in CHASE state
- Sleeping NPCs skip all behavior; woken by bump or combat

### Input Handling
- `InputManager` (core) maps `pygame.KEYDOWN` → `InputCommand` enum, context-aware by `GameStates`
- `InputController` (game/controllers) translates commands into `PlayerActionService` calls or UI window pushes — it must stay esper-free
- `PlayerActionService` (game/services) executes the actual game rules
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
| F9  | Save game (saves/save.json) |
| F10 | Load game |

## Common Pitfalls

1. **esper 3.x has no World class** — `esper` is the world. Don't try to instantiate `esper.World()`.
2. **`Stats` vs `EffectiveStats`** — Always read from `EffectiveStats` (or fall back to `Stats`). Write HP/mana changes to `Stats`. `EquipmentSystem` recomputes `EffectiveStats` each frame.
3. **Map freeze/thaw** — Entities not in `exclude_entities` get serialized into `MapContainer.frozen_entities` and deleted from esper. Always exclude the player party.
4. **Tile `walkable` property** — Registry-backed tiles use `_walkable` from `TileType`. Legacy tiles derive from sprite character. Don't set `walkable` directly.
5. **`SpriteLayer` in JSON** — Use the enum name string (e.g., `"ENTITIES"`), converted to enum at factory time.
6. **Event handlers** — `esper.set_handler()` persists across `clear_database()` only if `event_registry` isn't cleared. `reset_world()` clears both.

# ============================================================
# Verification Workflow (verify MCP server)
# ============================================================

## Verification Workflow (MANDATORY)

This project uses the `verify` MCP server for contract-based verification.
**Every code change MUST follow the Define → Work → Verify → Fix loop.**

### The Loop

1. **BEFORE writing code:** Call `verify_create_contract` with checks tailored to the task
2. **Write the code** as normal
3. **AFTER writing code:** Call `verify_run_contract` with the contract ID
4. **If FAILED:** Fix issues, run contract again. Repeat until it passes.
5. **Once PASSED:** Create the git commit (per existing rule: commit after every completed task)

**Never skip verification.** Not because you're "confident", not for small changes, not for JSON-only edits.

---

## Baseline Checks (ALWAYS include)

Every contract must include these three checks, adapted to the files you touched:

```json
[
  {
    "name": "syntax_valid",
    "check_type": {
      "type": "command_succeeds",
      "command": "python -m py_compile <CHANGED_FILE>",
      "working_dir": "."
    }
  },
  {
    "name": "imports_resolve",
    "check_type": {
      "type": "command_succeeds",
      "command": "python -c \"import <DOTTED_MODULE_PATH>\"",
      "working_dir": "."
    }
  },
  {
    "name": "full_test_suite",
    "check_type": {
      "type": "command_succeeds",
      "command": "python -m pytest tests/ -x -q --tb=short",
      "working_dir": ".",
      "timeout_secs": 120
    }
  }
]
```

Replace `<CHANGED_FILE>` with actual path (e.g. `game/systems/ai_system.py`) and `<DOTTED_MODULE_PATH>` with the Python import path (e.g. `game.systems.ai_system`).

---

## Check Templates by Area

Add these checks **on top of the baseline** depending on what you're changing:

### ECS Components (`game/components.py`)

```json
{
  "name": "component_is_dataclass",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/components.py",
    "required_patterns": ["@dataclass\\s*\\n\\s*class <NewComponent>"]
  }
},
{
  "name": "no_side_effect_methods_in_components",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "game/components.py",
    "forbidden_patterns": ["esper\\.dispatch_event", "esper\\.create_entity", "esper\\.delete_entity"]
  }
}
```

### ECS Frame Processors (`game/systems/`)

```json
{
  "name": "system_file_exists",
  "check_type": {
    "type": "file_exists",
    "path": "game/systems/<system_file>.py"
  }
},
{
  "name": "processor_has_process_method",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/systems/<system_file>.py",
    "required_patterns": ["def process\\(self"]
  }
},
{
  "name": "uses_esper_module_not_world_instance",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "game/systems/<system_file>.py",
    "forbidden_patterns": ["esper\\.World\\(", "self\\.world\\.", "world = esper\\.World"]
  }
},
{
  "name": "no_stored_entity_references",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "game/systems/<system_file>.py",
    "forbidden_patterns": ["self\\._entities", "self\\.entities", "self\\.player_entity"]
  },
  "severity": "warning"
},
{
  "name": "system_specific_tests_pass",
  "check_type": {
    "type": "command_succeeds",
    "command": "python -m pytest tests/verify_<system_name>.py -v --tb=short",
    "working_dir": ".",
    "timeout_secs": 60
  }
}
```

### MapAwareSystem Subclasses

If the system uses `MapAwareSystem`, add:

```json
{
  "name": "inherits_map_aware_system",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/systems/<system_file>.py",
    "required_patterns": ["MapAwareSystem", "def set_map\\(self"]
  }
},
{
  "name": "no_map_container_in_constructor",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "game/systems/<system_file>.py",
    "forbidden_patterns": ["def __init__\\(self,\\s*map_container"]
  }
}
```

### Services (`game/services/`)

```json
{
  "name": "service_test_exists",
  "check_type": {
    "type": "file_exists",
    "path": "tests/verify_<service_name>.py"
  },
  "severity": "warning"
},
{
  "name": "service_tests_pass",
  "check_type": {
    "type": "command_succeeds",
    "command": "python -m pytest tests/verify_<service_name>.py -v --tb=short",
    "working_dir": ".",
    "timeout_secs": 60
  }
},
{
  "name": "uses_logging_not_print",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/services/<service>.py",
    "required_patterns": ["import logging", "logger|log"]
  }
}
```

### JSON Data (`assets/data/`)

```json
{
  "name": "json_syntax_valid",
  "check_type": {
    "type": "command_succeeds",
    "command": "python -m json.tool assets/data/<file>.json > /dev/null",
    "working_dir": "."
  }
},
{
  "name": "all_json_files_valid",
  "check_type": {
    "type": "command_succeeds",
    "command": "python -c \"import json, glob; [json.load(open(f)) for f in glob.glob('assets/data/**/*.json', recursive=True)]\"",
    "working_dir": "."
  }
},
{
  "name": "sprite_layers_use_enum_names",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "assets/data/<file>.json",
    "forbidden_patterns": ["\"sprite_layer\":\\s*\\d"]
  },
  "severity": "warning"
}
```

### Entity/Item Templates (`game/content/`)

```json
{
  "name": "factory_function_exists",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/content/<factory_file>.py",
    "required_patterns": ["def create\\("]
  }
},
{
  "name": "uses_registry_not_hardcode",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/content/<factory_file>.py",
    "required_patterns": ["Registry\\.get|registry\\.get|_registry"]
  }
}
```

### Map Code (`game/map/`)

```json
{
  "name": "map_tests_pass",
  "check_type": {
    "type": "command_succeeds",
    "command": "python -m pytest tests/ -k 'map or tile or layer or portal' -v --tb=short",
    "working_dir": ".",
    "timeout_secs": 60
  }
},
{
  "name": "uses_tile_registry_not_hardcoded_props",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "game/map/<file>.py",
    "forbidden_patterns": ["walkable\\s*=\\s*(True|False)", "Tile\\(.*sprite="]
  },
  "severity": "warning"
},
{
  "name": "no_hardcoded_map_dimensions",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "game/map/<file>.py",
    "forbidden_patterns": ["range\\(80\\)", "range\\(50\\)", "width\\s*=\\s*80", "height\\s*=\\s*50"]
  },
  "severity": "warning"
}
```

### AI Behavior (`game/systems/ai_system.py`)

```json
{
  "name": "ai_tests_pass",
  "check_type": {
    "type": "command_succeeds",
    "command": "python -m pytest tests/verify_ai_system.py -v --tb=short",
    "working_dir": ".",
    "timeout_secs": 60
  }
},
{
  "name": "uses_ecs_query_not_stored_refs",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/systems/ai_system.py",
    "required_patterns": ["esper\\.get_component"]
  }
},
{
  "name": "has_traceability_comments",
  "check_type": {
    "type": "file_contains_patterns",
    "path": "game/systems/ai_system.py",
    "required_patterns": ["AISYS-|CHAS-|WNDR-"]
  },
  "severity": "info"
}
```

---

## Forbidden Patterns (global)

Include relevant subset in every contract:

```json
{
  "name": "no_print_statements",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "<file>",
    "forbidden_patterns": ["^\\s*print\\(", "breakpoint\\(\\)", "pdb\\.set_trace"]
  }
},
{
  "name": "no_esper_world_instantiation",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "<file>",
    "forbidden_patterns": ["esper\\.World\\("]
  }
},
{
  "name": "no_bare_except",
  "check_type": {
    "type": "file_excludes_patterns",
    "path": "<file>",
    "forbidden_patterns": ["except:\\s*$"]
  }
}
```

---

## Python-Specific Checks

These check types provide deeper Python analysis than generic command/pattern checks.

### Type Checking (mypy/pyright)

Use instead of `command_succeeds` with mypy — gives structured error counts and details:

```json
{
  "name": "type_check_systems",
  "check_type": {
    "type": "python_type_check",
    "paths": ["game/systems/", "services/"],
    "checker": "mypy",
    "extra_args": ["--ignore-missing-imports"],
    "working_dir": "."
  },
  "severity": "warning"
}
```

### Structured Pytest Results

Use instead of `command_succeeds` with pytest — enforces thresholds on pass/fail/skip:

```json
{
  "name": "test_suite_quality",
  "check_type": {
    "type": "pytest_result",
    "test_path": "tests/ -x --tb=short",
    "min_passed": 40,
    "max_failures": 0,
    "max_skipped": 5,
    "working_dir": "."
  }
}
```

For system-specific tests:

```json
{
  "name": "ai_system_tests",
  "check_type": {
    "type": "pytest_result",
    "test_path": "tests/verify_ai_system.py -v",
    "min_passed": 5,
    "max_failures": 0,
    "working_dir": "."
  }
}
```

### Circular Import Detection

**Use this on every change that adds new imports between packages.** The ECS architecture
with components, systems, services, and entities has high circular import risk:

```json
{
  "name": "no_circular_imports_ecs",
  "check_type": {
    "type": "python_import_graph",
    "root_path": "ecs",
    "fail_on_circular": true,
    "working_dir": "."
  }
},
{
  "name": "no_circular_imports_services",
  "check_type": {
    "type": "python_import_graph",
    "root_path": "services",
    "fail_on_circular": true,
    "working_dir": "."
  }
},
{
  "name": "no_circular_imports_entities",
  "check_type": {
    "type": "python_import_graph",
    "root_path": "entities",
    "fail_on_circular": true,
    "working_dir": "."
  }
}
```

### JSON ↔ Registry Consistency

Verify that all IDs defined in JSON data files are actually registered/used in Python code.
**Use this when adding new entities, items, tiles, or schedules:**

```json
{
  "name": "all_entity_ids_registered",
  "check_type": {
    "type": "json_registry_consistency",
    "json_path": "assets/data/entities.json",
    "id_field": "id",
    "source_path": "game/content/entity_registry.py"
  }
},
{
  "name": "all_item_ids_registered",
  "check_type": {
    "type": "json_registry_consistency",
    "json_path": "assets/data/items.json",
    "id_field": "id",
    "source_path": "game/content/item_registry.py"
  }
},
{
  "name": "all_tile_ids_registered",
  "check_type": {
    "type": "json_registry_consistency",
    "json_path": "assets/data/tile_types.json",
    "id_field": "id",
    "source_path": "game/map/tile_registry.py"
  }
},
{
  "name": "all_schedule_ids_registered",
  "check_type": {
    "type": "json_registry_consistency",
    "json_path": "assets/data/schedules.json",
    "id_field": "id",
    "source_path": "game/content/schedule_registry.py"
  }
}
```

---

## Quick Check Examples

Use `verify_quick_check` for ad-hoc checks during work:

**"Does the game still import?"**
```json
{ "check": { "name": "game_imports", "check_type": { "type": "command_succeeds", "command": "python -c \"from game.states import GameplayState\"", "working_dir": "." } } }
```

**"Do the smoke tests pass?"**
```json
{ "check": { "name": "smoke", "check_type": { "type": "command_succeeds", "command": "python -m pytest tests/verify_smoke*.py -v --tb=short", "working_dir": ".", "timeout_secs": 60 } } }
```

**"Is this JSON valid?"**
```json
{ "check": { "name": "json_ok", "check_type": { "type": "command_succeeds", "command": "python -m json.tool assets/data/scenarios/village.json > /dev/null", "working_dir": "." } } }
```

---

## Full Contract Example: Adding a New ECS Phase System

Task: "Add ScheduleSystem that processes NPC schedules during ENEMY_TURN"

```json
{
  "description": "New ScheduleSystem phase system",
  "task": "Create ScheduleSystem that updates NPC Activity components based on WorldClockService time during ENEMY_TURN phase",
  "checks": [
    {
      "name": "syntax_valid",
      "check_type": { "type": "command_succeeds", "command": "python -m py_compile game/systems/schedule_system.py", "working_dir": "." }
    },
    {
      "name": "imports_resolve",
      "check_type": { "type": "command_succeeds", "command": "python -c \"from game.systems.schedule_system import ScheduleSystem\"", "working_dir": "." }
    },
    {
      "name": "file_exists",
      "check_type": { "type": "file_exists", "path": "game/systems/schedule_system.py" }
    },
    {
      "name": "has_process_method",
      "check_type": { "type": "file_contains_patterns", "path": "game/systems/schedule_system.py", "required_patterns": ["def process\\(self"] }
    },
    {
      "name": "queries_schedule_and_activity",
      "check_type": { "type": "file_contains_patterns", "path": "game/systems/schedule_system.py", "required_patterns": ["esper\\.get_component", "Schedule", "Activity"] }
    },
    {
      "name": "uses_esper_module_level",
      "check_type": { "type": "file_excludes_patterns", "path": "game/systems/schedule_system.py", "forbidden_patterns": ["esper\\.World\\(", "self\\.world"] }
    },
    {
      "name": "no_stored_entity_refs",
      "check_type": { "type": "file_excludes_patterns", "path": "game/systems/schedule_system.py", "forbidden_patterns": ["self\\._entities", "self\\.player_ent"] },
      "severity": "warning"
    },
    {
      "name": "no_print",
      "check_type": { "type": "file_excludes_patterns", "path": "game/systems/schedule_system.py", "forbidden_patterns": ["^\\s*print\\("] }
    },
    {
      "name": "uses_logging",
      "check_type": { "type": "file_contains_patterns", "path": "game/systems/schedule_system.py", "required_patterns": ["import logging"] },
      "severity": "warning"
    },
    {
      "name": "test_file_exists",
      "check_type": { "type": "file_exists", "path": "tests/verify_schedule_system.py" },
      "severity": "warning"
    },
    {
      "name": "all_tests_structured",
      "check_type": {
        "type": "pytest_result",
        "test_path": "tests/ -x --tb=short",
        "min_passed": 40,
        "max_failures": 0,
        "working_dir": "."
      }
    },
    {
      "name": "no_circular_imports_ecs",
      "check_type": {
        "type": "python_import_graph",
        "root_path": "ecs",
        "fail_on_circular": true,
        "working_dir": "."
      }
    },
    {
      "name": "schedule_ids_consistent",
      "check_type": {
        "type": "json_registry_consistency",
        "json_path": "assets/data/schedules.json",
        "id_field": "id",
        "source_path": "game/content/schedule_registry.py"
      }
    },
    {
      "name": "type_check",
      "check_type": {
        "type": "python_type_check",
        "paths": ["game/systems/schedule_system.py"],
        "checker": "mypy",
        "extra_args": ["--ignore-missing-imports"],
        "working_dir": "."
      },
      "severity": "warning"
    },
    {
      "name": "diff_is_focused",
      "check_type": { "type": "diff_size_limit", "max_additions": 250, "max_deletions": 50 },
      "severity": "warning"
    }
  ]
}
```