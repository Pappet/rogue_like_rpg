# Rogue Like RPG

A turn-based roguelike RPG / living-world simulation built with **Python**,
**Pygame**, and **esper** (Entity Component System). Travel an ASCII world of
settlements that live on their own — townsfolk work, trade, gossip and sleep
whether you are there or not — take on quests that grow out of the simulation,
trade along price differences, craft, and fight your way through the wilds.

> Design goal: *"Skyrim, but smaller and more alive — the world does not wait
> for the player."* The full direction lives in [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Features

**World & exploration**

- 🗺️ **Multi-layer maps** with portals connecting interiors and exteriors
- 🌍 **Overworld travel** between settlements (Village, Brackenfen, Eastmoor) and POIs
- 👁️ **Field of view** via shadowcasting with fog-of-war memory decay
- 🌅 **Day/night cycle** with smooth viewport tinting and light sources
- 🕵️ **Hidden secrets** revealed by getting close (perception-gated)
- 💾 **Save / load** a full session snapshot (F9 / F10); a `--seed` makes a run reproducible

**The living world**

- 🏘️ **NPC schedules** — work, socialise, patrol and sleep by the world clock
- 🧠 **Off-screen simulation** — settlements keep ticking while you're away, reconciled on arrival
- 🍖 **Needs** — a hungry NPC abandons its schedule to eat
- 🗣️ **Gossip & relationships** — named townsfolk chatter about people they actually know
- 🛡️ **Factions & reputation** — kills and favours move your standing; spill enough blood and the guard turns on you
- 📜 **Quests & chains** — authored *and* simulation-generated (a smith short of ore posts a delivery; a wolf sighting becomes a hunt)
- 💬 **Conditional dialogue & rumors** — lines react to time, reputation, quest and prosperity state

**Player systems**

- ⚔️ **Turn-based combat** with critical hits, bleeding, floating combat text and loot drops
- 🎒 **Inventory & equipment** with weight limits and gear slots
- 💰 **Trade & economy** — per-settlement stock drives prices; haul goods for profit
- 🔧 **Crafting** at stations (forge, anvil, mill, oven, tannery, herbalist, jeweler) with skill-based quality/quantity
- ⛏️ **Gathering** from resource nodes (herbs, ore, grain) that respawn over time
- 📈 **Learn-by-doing skills** — crafting, gathering and combat train with use
- 🔧 **Debug overlays** — toggle FOV, chase lines, AI state labels

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the shipped feature phases (A–L)
and [`CLAUDE.md`](CLAUDE.md) for the full architecture reference.

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py

# Run with a fixed world seed (reproducible run)
python main.py --seed 12345
```

### Requirements

- Python 3.10+
- pygame 2.6.x
- esper 3.x
- pathfinding 1.x

(Exact pinned versions are in [`requirements.txt`](requirements.txt).)

## Controls

| Key | Action |
|-----|--------|
| Arrow Keys | Move / navigate menus |
| W / S | Cycle selected action |
| G | Interact — pickup, enter portal, talk, trade, craft, rest (bump the target) |
| Space | Wait one turn |
| I | Open inventory |
| C | Open character sheet (stats & skills) |
| M | Open the world map / travel |
| J | Open the quest journal |
| X | Examine mode |
| Enter | Confirm / interact / travel |
| Escape | Cancel / close |
| Tab | Cycle target (while targeting) |

In the **inventory**: `U` use, `E` equip, `D` drop. Trade, crafting, rest and
quest windows open by **bumping** the relevant NPC or tile (a merchant, a
crafting station, a bed/innkeeper, a quest giver).

### Debug Controls

| Key | Action |
|-----|--------|
| F3 | Toggle debug master |
| F4 | Toggle player FOV overlay |
| F5 | Toggle NPC FOV overlay |
| F6 | Toggle chase target lines |
| F7 | Toggle AI state labels |
| F9 | Save game (`saves/save.json`) |
| F10 | Load game |

## Architecture

The game uses an **Entity Component System** (ECS) powered by
[esper 3.x](https://github.com/benmoran56/esper) (module-level, no `World`
instance). A `bootstrap.build_game_context()` composition root wires everything
once into a typed `GameContext`; thin `GameState` subclasses delegate to
controllers (`InputController`, `TurnOrchestrator`, `RenderPipeline`).

```
GameController ──▶ GameState (TitleScreen, GameplayState, WorldMapState, GameOver)
                         │  delegates to controllers — no game rules in states
                         ▼
                   esper ECS (module-level)
                   ┌──────────────┐
                   │  Components   │  Plain dataclasses (Position, Stats, AI, ...)
                   │  Systems      │  Frame processors, phase systems, event handlers
                   │  Events       │  "Facts up, commands down" via dispatch/handler
                   └──────────────┘
```

**System categories:**

- **Frame processors** — run every frame via `esper.process()` (TurnSystem, MovementSystem, CombatSystem, ...)
- **Phase systems** — called during the enemy turn (AISystem, ScheduleSystem, NeedsSystem, GossipSystem, ...)
- **Render systems** — called during `draw()` (RenderSystem, UISystem, DebugRenderSystem)
- **Event systems** — react to events only, no process loop (DeathSystem)

A machine-checked layering rule keeps `core/` game-agnostic: it must never
import from `game/`. All game content is **data-driven** via JSON in
`assets/data/`.

## Testing

Tests live in `tests/`, named `verify_*.py` (plus `test_smoke.py`):

```bash
# Run the full suite
python -m pytest tests/ -q

# Run a single test
python -m pytest tests/verify_ai_system.py -v
```

CI (`.github/workflows/ci.yml`) runs `ruff check`, `ruff format --check` and
the full suite on Python 3.10 and 3.12 (headless SDL) for every PR and push to
`main`.

## Project Structure

```
├── main.py                  # Entry point: GameController + main loop
├── bootstrap.py             # Composition root: builds the GameContext once
├── game_context.py          # GameContext / Systems / DebugFlags dataclasses
├── config/                  # Constants & enums (game, ui, colors, debug, enums)
├── core/                    # Game-agnostic layer (never imports game/)
│   ├── ecs.py, camera.py, input_manager.py, rng.py, registry.py
│   ├── visibility_service.py, world_clock_service.py
│   └── ui/                  # UIStack, MessageLog, theme, window base
├── game/                    # Game layer (may use core/)
│   ├── components.py        # All ECS component dataclasses
│   ├── systems/             # 17 ECS systems
│   ├── services/            # 32 game-rule / world services
│   ├── content/             # Registries, factories, ContentDatabase
│   ├── map/                 # Tile, MapLayer, MapContainer, generation
│   ├── controllers/         # InputController, TurnOrchestrator, RenderPipeline
│   ├── states/              # TitleScreen, GameplayState, WorldMapState, GameOver
│   └── ui/windows/          # 7 modal windows (inventory, trade, crafting, ...)
├── assets/data/             # JSON game content (+ prefabs/, scenarios/)
├── tests/                   # 93 test files (verify_*.py + test_smoke.py)
└── docs/                    # ROADMAP, DEV_JOURNAL, ARCHITECTURE_CONCEPT, CONTENT_GUIDE, ...
```

See [`CLAUDE.md`](CLAUDE.md) for the full architecture reference and the
playbook for adding features, and [`PROJECT_OVERVIEW.md`](PROJECT_OVERVIEW.md)
for the key architectural decisions. For authoring JSON content (settlements,
items, entities, biomes), see the data-driven content reference
[`docs/CONTENT_GUIDE.md`](docs/CONTENT_GUIDE.md).

## License

Private project — all rights reserved.
</content>
</invoke>
