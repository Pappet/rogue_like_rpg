# Technology Stack

**Analysis Date:** 2026-02-14

## Languages

**Primary:**
- Python 3.13.11 - Core game engine and all business logic

## Runtime

**Environment:**
- Python 3.13.11 (standard CPython)

**Package Manager:**
- pip (system-level dependencies)
- No lockfile detected (dependencies installed via direct imports)

## Frameworks

**Core:**
- Pygame 1.x+ - 2D graphics rendering, event handling, display management (`/home/peter/Projekte/rogue_like_rpg/main.py:1`, `/home/peter/Projekte/rogue_like_rpg/services/render_service.py:1`)
- Esper 3.x+ - Entity Component System (ECS) framework for game entity management (`/home/peter/Projekte/rogue_like_rpg/ecs/world.py:1`)

**Architecture:**
- Custom MVC-inspired game state pattern with state transitions (`/home/peter/Projekte/rogue_like_rpg/game_states.py:19-65`)
- Service layer pattern for domain concerns (`/home/peter/Projekte/rogue_like_rpg/services/`)

## Key Dependencies

**Critical:**
- pygame - Used for all rendering, font management, event handling, display surfaces
  - Location: Used throughout, primary locations: `services/render_service.py`, `main.py`, `game_states.py`
  - Initialization: `pygame.init()` called in main entry point
  - Font handling: `pygame.font.SysFont()` for monospace rendering at TILE_SIZE pixels

- esper - Entity Component System framework for game entity and system management
  - Location: `ecs/world.py`, all systems in `ecs/systems/`, entity creation in services
  - Core interface: `esper.create_entity()`, `esper.clear_database()`, component iteration
  - Version: 3.x (using module-level world state)

**Standard Library Only:**
- dataclasses - Used for component definitions (`ecs/components.py`)
- enum - Used for game states and sprite layers (`config.py`)
- typing - Type hints throughout codebase
- re - Regular expression parsing for message log rich text (`ui/message_log.py:2`)
- math - Used for visibility calculations (`services/visibility_service.py:1`)
- random - Used for terrain variety (`services/map_service.py:40`)

## Configuration

**Environment:**
- No `.env` files or environment variables required
- All game configuration hardcoded in `config.py`:
  - Screen dimensions: 800x600 pixels
  - Tile size: 32 pixels
  - UI dimensions: 48px header, 160px sidebar, 140px log

**Build:**
- No build system. Direct Python execution via `python main.py`
- Entry point: `main.py` containing `main()` function

## Platform Requirements

**Development:**
- Python 3.13.11+
- Pygame library (graphical framework)
- Linux/macOS/Windows with display support

**Production/Runtime:**
- Python 3.13.11 runtime
- Pygame and dependencies
- Display capabilities (X11/Wayland on Linux, native on macOS/Windows)
- Graphics hardware acceleration (OpenGL-based, Pygame-managed)

## Data Persistence

**Current State:**
- No persistent data storage implemented
- Game state lives entirely in memory during runtime
- No database integration
- ECS world state reset between sessions via `esper.clear_database()`

---

*Stack analysis: 2026-02-14*
