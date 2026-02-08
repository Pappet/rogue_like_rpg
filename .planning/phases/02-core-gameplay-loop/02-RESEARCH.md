# Phase 2: Core Gameplay Loop - Research

**Researched:** 2024-07-25
**Domain:** Pygame, Rogue-like Architecture
**Confidence:** HIGH

## Summary

This research document outlines the standard techniques and architectural patterns for implementing a tile-based, turn-based rogue-like RPG using Pygame. The findings are based on the specific requirements detailed in the `CONTEXT.md` file for this phase.

The core of the architecture revolves around a state machine for turn management, a layered rendering system using Pygame's built-in sprite groups, and a clear data hierarchy for managing game world maps. The player's party is treated as a single entity on the map, simplifying movement and interaction logic. Special rendering effects like "see-through" maps are achievable by layering surfaces with transparency.

**Primary recommendation:** Adhere to the standard Pygame idioms of using `pygame.sprite.Sprite` and `pygame.sprite.LayeredUpdates` for all game objects. This provides a robust foundation for rendering order and grouping. Manage game state explicitly (e.g., `PLAYER_TURN`, `ENEMY_TURN`) to enforce the turn-based logic.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Tile & Map Appearance
- **Map Containers:** The game world is organized into "map containers", which represent areas like dungeons or towns. A container can hold multiple layers (levels).
- **Map Layers:** Each container can have one or more layers, which are the individual tilemaps (e.g., floors of a building).
- **Transitions:** Players can transition between layers within a container (e.g., using stairs) and between different containers (e.g., entering a house). These transitions can have visual effects.
- **Map Generation:** Maps within a container will have determinate dimensions but can be generated in different sizes.
- **Visual Style:** The game will use a tilemap-based visual style (e.g., pixel art).
- **Fog of War:** The map will be covered by a "fog of war" that is revealed as the player explores.
- **"See-Through" Feature:** It should be possible to see the layer below the player's current position through holes or other visual effects.
- **Special Effects:** The game should support special effects animations on tiles, such as animated water, poison fog, cold areas, and explosions.

### Turn-Based Flow
- **Turn Order:** The player always acts first. After the player's turn, all enemies act based on an initiative order.
- **Initiative:** Initiative will be calculated based on a character attribute and other modifiers.
- **Player Actions:** A player's turn can consist of one of the following actions:
    - Moving (which also triggers enemy turns).
    - Casting a defensive spell (e.g., healing, buffs).
    - Using a potion from inventory.
    - Using the "investigation mode" to examine a tile.
    - Using the "range-attack mode" for ranged attacks or spells.
- **Waiting:** The player can choose to wait, which ends their turn without any other action.
- **Buffs/Debuffs:** Buffs and debuffs will have a duration measured in a number of turns.
- **Turn Indicator:** A text-based indicator will be displayed to inform the player that it is their turn to act.

### Player Party & Movement
- **UI Layout:** The screen will be divided into sections, including a map view and a party list UI.
- **Party Representation:** The player's party is represented as a single sprite on a single tile on the map.
- **Party Control:** The party is always selected by default and moves as a single unit. Movement animation will be a simple slide.
- **Individual Hero Status:** The party list UI will display the status of each hero. The player can select a hero from this list to use their specific actions.
- **Hero Death:** When a hero dies, they are marked as "dead" in the party list and can no longer be selected for actions.
- **Roster Management:** The player's party roster is not fixed. The player can hire new heroes and leave others behind.

### Sprite Layering
- **Layer System:** A tile can contain multiple sprites, but each must be on a different layer.
- **Layer Order:** There is a fixed rendering order for the layers:
    - Layer 0: Ground (e.g., floor, walls)
    - Layer 1: Decor (Bottom) (e.g., rugs)
    - Layer 2: Traps
    - Layer 3: Items
    - Layer 4: Corpses
    - Layer 5: Entities (Player and Enemies)
    - Layer 6: Decor (Top) (e.g., chandeliers)
    - Layer 7: Effects (e.g., explosions)
- **Flexibility:** The system should be flexible enough to allow for new layers to be added later.
- **Corpse Sprites:** Dead enemies are represented by a corpse sprite that does not despawn.
- **UI Element:** The UI will include an element that displays the stack of sprites on the tile the player is currently standing on.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pygame` | `2.x` | Core game framework | The required foundation for the project. Provides rendering, input, and sprite management. |

### Supporting
*No external libraries beyond Pygame are strictly necessary for this phase, but `numpy` could be considered for map data manipulation if performance with large maps becomes an issue.*

**Installation:**
```bash
pip install pygame
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── components/      # Reusable game components (e.g., Fighter, Item)
├── entities/        # Game object classes (Player, Enemy, ItemObject)
├── game_map/        # Map, Tile, and Container classes
├── rendering/       # Rendering logic, camera
├── systems/         # Game logic systems (e.g., turn management, combat)
└── main.py          # Main game loop
```

### Pattern 1: Layered Rendering with `LayeredUpdates`
**What:** Use Pygame's `pygame.sprite.LayeredUpdates` group to manage all visible sprites. Each sprite is assigned a `_layer` attribute that dictates its rendering order, automatically handling the complex layering requirements.
**When to use:** For all rendering of in-game objects to ensure they appear in the correct visual order (e.g., player on top of floor, effects on top of player).
**Example:**
```python
# Source: https://www.pygame.org/docs/ref/sprite.html#pygame.sprite.LayeredUpdates
import pygame

# Define layer constants for readability
class RenderLayer:
    GROUND = 0
    DECOR_BOTTOM = 1
    TRAPS = 2
    ITEMS = 3
    CORPSES = 4
    ENTITIES = 5
    DECOR_TOP = 6
    EFFECTS = 7

class GameObject(pygame.sprite.Sprite):
    def __init__(self, layer, *groups):
        super().__init__(*groups)
        self._layer = layer
        # ... other setup ...

# In your main setup
all_sprites = pygame.sprite.LayeredUpdates()

# When creating objects
player = GameObject(layer=RenderLayer.ENTITIES, groups=all_sprites)
rug = GameObject(layer=RenderLayer.DECOR_BOTTOM, groups=all_sprites)

# In your main loop
all_sprites.draw(screen) # Draws all sprites in correct layer order
```

### Pattern 2: Turn-Based State Machine
**What:** A state machine that controls the flow of the game. The main loop checks the current state and only processes relevant logic. This prevents real-time updates and enforces the turn-based structure.
**When to use:** To manage the overall game flow between player turns and enemy turns.
**Example:**
```python
from enum import Enum, auto

class GameState(Enum):
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()
    # ... other states like INVENTORY, TARGETING ...

game_state = GameState.PLAYER_TURN

# In the main game loop
if game_state == GameState.PLAYER_TURN:
    # process_player_input() looks for key presses, mouse clicks
    action = process_player_input()
    if action:
        # Perform player action
        game_state = GameState.ENEMY_TURN

elif game_state == GameState.ENEMY_TURN:
    # Loop through enemies sorted by initiative
    for enemy in sorted(enemies, key=lambda e: e.initiative, reverse=True):
        enemy.perform_ai_action()
    
    # After all enemies act, return to player
    game_state = GameState.PLAYER_TURN
```

### Pattern 3: World Data Structure
**What:** A nested data structure to manage map containers and their levels. A top-level `World` object contains multiple `MapContainer`s, each of which contains multiple `GameMap` levels.
**When to use:** To organize the game world and facilitate transitions between maps and levels.
**Example:**
```python
class World:
    def __init__(self):
        self.containers = {
            "dungeon_1": MapContainer(...),
            "town": MapContainer(...)
        }

class MapContainer:
    def __init__(self):
        self.levels = [
            GameMap(level_data_floor_1),
            GameMap(level_data_floor_2)
        ]

# Game manager tracks current location
current_container = "dungeon_1"
current_level_index = 0
player_pos = (10, 15)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sprite Layering | A custom list-sorting render loop | `pygame.sprite.LayeredUpdates` | It's a highly optimized, built-in solution for exactly this problem. It's less error-prone and more performant than a manual implementation. |
| Basic Vector Math | Manual tuple arithmetic | `pygame.math.Vector2` | Provides clean, readable methods for vector operations (addition, scaling, distance), which are common in grid-based movement and distance checks. |

## Common Pitfalls

### Pitfall 1: Blocking for Player Input
**What goes wrong:** The game loop freezes entirely while waiting for a `pygame.event.wait()` or a blocking input loop, making the application unresponsive.
**Why it happens:** Failing to process the event queue continuously.
**How to avoid:** Always use a non-blocking event polling loop (`for event in pygame.event.get()`). Manage turns with a state machine, not by pausing the loop. The loop should always be running, drawing the screen, and checking the current game state every frame.

### Pitfall 2: Incorrect Transparency Handling
**What goes wrong:** Transparent parts of PNG images appear as solid black, or entire surfaces lose their per-pixel transparency.
**Why it happens:** Forgetting to call `.convert_alpha()` on surfaces loaded from images with alpha channels.
**How to avoid:** Always use `pygame.image.load("path.png").convert_alpha()` for any sprite or tile image that has transparency.

### Pitfall 3: Mutable Default Arguments
**What goes wrong:** Multiple game objects created from the same class share data unexpectedly, like all enemies sharing the same inventory list.
**Why it happens:** Using mutable types (like `[]` or `{}`) as default arguments in a class `__init__` method. This creates one shared instance of the mutable type.
**How to avoid:** Use `None` as the default and create a new mutable object inside `__init__`.
```python
# Bad
def __init__(self, inventory=[]):
    self.inventory = inventory # All instances share this list

# Good
def __init__(self, inventory=None):
    if inventory is None:
        self.inventory = []
    else:
        self.inventory = inventory
```

## Code Examples

### "See-Through" Map Rendering
**Concept:** Render the lower level map to the screen first. Then, render the current level map over it. Tiles on the current map that are "holes" must be fully transparent in their image file (e.g., PNG with alpha).
```python
# Source: Synthesis of Pygame rendering principles
# Assume 'level_0_surface' and 'level_1_surface' are pre-rendered
# surfaces for each map level. 'level_1_surface' has holes with
# per-pixel alpha transparency.

# In the main render function:
camera_offset = ...

# 1. Draw the level BELOW the player
screen.blit(level_0_surface, camera_offset)

# 2. Draw the player's CURRENT level on top
screen.blit(level_1_surface, camera_offset)

# 3. Draw all sprites (player, enemies, items)
all_sprites.draw(screen) # LayeredUpdates handles their order
```

## Open Questions

1. **Performance of "See-Through" Maps:**
   - **What we know:** The proposed method of blitting one full-map surface over another is simple to implement.
   - **What's unclear:** The performance impact on very large maps is unknown. Re-rendering entire map surfaces every frame could be slow.
   - **Recommendation:** For initial implementation, pre-render each map layer to a single surface when the level is loaded. Only re-render if the map itself changes (e.g., a wall is destroyed). If performance is an issue, a more complex approach of only drawing visible portions (camera view) of each layer will be necessary.

## Sources

### Primary (HIGH confidence)
- Pygame Documentation: `sprite.LayeredUpdates`, `Surface.convert_alpha()`, `event` handling.
- `CONTEXT.md` for this phase, which defined the specific requirements.

### Secondary (MEDIUM confidence)
- Various web tutorials on Pygame rogue-like development, confirming the state machine and layered rendering patterns.
- Stack Overflow discussions on Pygame transparency and rendering order.
