# Rogue Like RPG

A turn-based roguelike RPG built with **Python**, **Pygame**, and **esper** (Entity Component System). Explore a tile-based ASCII world with day/night cycles, NPC schedules, multi-layer maps, and tactical combat.

## Features

- 🗺️ **Multi-layer maps** with portals connecting interiors and exteriors
- ⚔️ **Turn-based combat** with floating combat text and loot drops
- 🌅 **Day/night cycle** with smooth viewport tinting and NPC schedules
- 👁️ **Field of view** via shadowcasting — explore the fog of war
- 🧭 **A\* pathfinding** for NPC navigation and chasing
- 🎒 **Inventory & equipment** system with weight limits and gear slots
- 💬 **Dialogue system** for NPC conversations
- 🏘️ **Data-driven villages** — maps, NPCs, items, and schedules defined in JSON
- 🔧 **Debug overlays** — toggle FOV, chase lines, AI state labels

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

### Requirements

- Python 3.10+
- pygame ≥ 2.5
- esper ≥ 3.0
- pathfinding ≥ 1.0

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys | Move / navigate menus |
| Enter | Confirm / interact |
| Escape | Cancel / close |
| G | Interact (pickup / portal) |
| I | Open inventory |
| C | Open character sheet |
| M | Toggle world map |
| X | Examine mode |
| W / S | Cycle actions |
| Space | Wait |

### Debug Controls

| Key | Action |
|-----|--------|
| F3 | Toggle debug master |
| F4 | Toggle player FOV overlay |
| F5 | Toggle NPC FOV overlay |
| F6 | Toggle chase target lines |
| F7 | Toggle AI state labels |

## Architecture

The game uses an **Entity Component System** (ECS) architecture powered by [esper 3.x](https://github.com/benmoran56/esper):

```
GameController ──▶ GameState subclasses (TitleScreen, Game, WorldMapState, GameOver)
                         │
                         ▼
                   esper ECS (module-level)
                   ┌──────────────┐
                   │  Components   │  Plain dataclasses (Position, Stats, AI, ...)
                   │  Systems      │  Frame processors, phase systems, event handlers
                   │  Events       │  Cross-system communication via dispatch/handler
                   └──────────────┘
```

**System categories:**

- **Frame Processors** — run every frame via `esper.process()` (TurnSystem, CombatSystem, ...)
- **Phase Systems** — called manually during specific game phases (AISystem, ScheduleSystem)
- **Render Systems** — called during `draw()` (RenderSystem, UISystem, DebugRenderSystem)
- **Event Systems** — react to events only, no process loop (DeathSystem)

All game content is **data-driven** via JSON files in `assets/data/`.

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run smoke tests only
python -m pytest tests/test_smoke.py -v
```

## Project Structure

```
├── main.py                  # Entry point
├── game_states.py           # State machine
├── config/                  # Constants & enums
├── ecs/
│   ├── components.py        # All ECS components
│   └── systems/             # 14 system files
├── entities/                # Entity/item factories & registries
├── map/                     # Tile, MapLayer, MapContainer
├── services/                # 17 service modules
├── ui/                      # Message log, UIStack, windows
├── assets/data/             # JSON game data
└── tests/                   # 52 test files
```

See [CLAUDE.md](CLAUDE.md) for full architectural documentation.

## License

Private project — all rights reserved.
