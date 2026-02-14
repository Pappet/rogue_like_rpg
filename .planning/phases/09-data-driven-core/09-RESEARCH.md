# Phase 09: Data-Driven Core - Research

**Researched:** 2024-05-22
**Domain:** Resource Management & Data-Driven Architecture
**Confidence:** HIGH

## Summary

This phase transitions the game from hardcoded tile properties (character, transparency, walkability) to a data-driven system using JSON. This separates content design from code, allowing easier addition of new terrain types and modifying game balance without recompilation.

The core solution involves a `ResourceLoader` that parses `tile_types.json` into a `TileRegistry`. The `Tile` class will be refactored to initialize its state from these registry definitions using a `type_id`, while retaining the ability to diverge (e.g., procedural variations or dynamic state like open/closed doors).

**Primary recommendation:** Implement a `TileRegistry` populated by `json` loader, and refactor `Tile` to instantiate properties from this registry based on a string `type_id`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` | Python Std | Data Serialization | Native, human-readable, widely supported. |
| `dataclasses` | Python Std | Data Structure | lightweight immutable containers for `TileType`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `enum` | Python Std | Layer Definitions | Mapping JSON string keys to `SpriteLayer` enums. |

## Architecture Patterns

### Recommended Project Structure
```
data/
└── tile_types.json  # New resource file
services/
└── resource_loader.py # New service
map/
├── tile_registry.py   # New registry module
└── tile.py            # Refactored
```

### Pattern 1: Flyweight / Prototype-Instance
**What:** `TileType` (Flyweight) holds shared immutable data (base name, default sprite). `Tile` (Instance) copies these defaults but maintains its own mutable state (visibility, dynamic sprite changes).
**When to use:** When you have thousands of objects (tiles) that share common properties but need individual state (fog of war).

**Example:**
```python
# map/tile_registry.py
@dataclass
class TileType:
    id: str
    name: str
    walkable: bool
    transparent: bool
    sprites: Dict[SpriteLayer, str]
    color: Tuple[int, int, int]
    base_description: str

class TileRegistry:
    _registry = {}
    
    @classmethod
    def register(cls, tile_type: TileType):
        cls._registry[tile_type.id] = tile_type
        
    @classmethod
    def get(cls, type_id: str) -> TileType:
        return cls._registry.get(type_id)
```

### Pattern 2: Service-Based Loading
**What:** `ResourceLoader` is a service called during `Game.startup()` to populate static registries.
**Why:** Ensures all data is available before any map generation occurs.

## JSON Schema

The `tile_types.json` should follow this schema:

```json
[
  {
    "id": "floor_stone",
    "name": "Stone Floor",
    "base_description": "A cold, uneven stone floor.",
    "walkable": true,
    "transparent": true,
    "sprites": {
      "GROUND": "."
    },
    "color": [200, 200, 200]
  },
  {
    "id": "wall_stone",
    "name": "Stone Wall",
    "base_description": "A solid wall of rough-hewn stone.",
    "walkable": false,
    "transparent": false,
    "sprites": {
      "GROUND": "#"
    },
    "color": [100, 100, 100],
    "occludes_below": false
  },
  {
    "id": "roof_thatch",
    "name": "Thatched Roof",
    "base_description": "A dried straw roof.",
    "walkable": true,
    "transparent": false,
    "sprites": {
      "GROUND": "#"
    },
    "color": [150, 110, 50],
    "occludes_below": true
  }
]
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Parsing | Custom string splitter | `json.load()` | Handling nested objects, escape characters, and errors is complex. |
| Global Access | Passing registry everywhere | Singleton/Module State | Tile definitions are static global constants effectively. |

## Common Pitfalls

### Pitfall 1: Hardcoded Character Checks
**What goes wrong:** Code checks `if tile.sprite == '#'` to determine wall logic.
**Why it happens:** Legacy code relied on visuals for logic.
**How to avoid:** Use `tile.walkable` or check `tile.type_id`. **Audit existing code** (found ~1400 matches for chars, need careful refactor).
**Refactor Target:** `map_generator_utils.py` and `MapService` logic relying on literal `#`.

### Pitfall 2: Circular Imports
**What goes wrong:** `Tile` imports `TileRegistry`, but `TileRegistry` might need `Tile` (if not careful).
**How to avoid:** Define `TileType` data class independently. `Tile` depends on `TileRegistry`. `TileRegistry` depends on nothing but `TileType`.

### Pitfall 3: Mutable Defaults
**What goes wrong:** Modifying the `sprites` dict of a `Tile` affects the `TileType` if not copied.
**Prevention:** `self.sprites = tile_type.sprites.copy()` in `Tile.__init__`.

## Code Examples

### Resource Loader Implementation
```python
# services/resource_loader.py
import json
import os
from map.tile_registry import TileRegistry, TileType
from config import SpriteLayer

class ResourceLoader:
    @staticmethod
    def load_tiles(filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Resource file not found: {filepath}")
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        for item in data:
            # Convert string keys to Enum for sprites
            sprites = {}
            for layer_name, char in item.get("sprites", {}).items():
                try:
                    layer = SpriteLayer[layer_name]
                    sprites[layer] = char
                except KeyError:
                    print(f"Warning: Unknown sprite layer {layer_name} in tile {item['id']}")
            
            tile_type = TileType(
                id=item["id"],
                name=item["name"],
                base_description=item.get("base_description", ""),
                walkable=item["walkable"],
                transparent=item["transparent"],
                sprites=sprites,
                color=tuple(item.get("color", (255, 255, 255))),
                occludes_below=item.get("occludes_below", False)
            )
            TileRegistry.register(tile_type)
```

### Refactored Tile Class
```python
# map/tile.py
from map.tile_registry import TileRegistry

class Tile:
    def __init__(self, type_id: str):
        self.type_id = type_id
        
        # Fetch base definition
        tile_type = TileRegistry.get(type_id)
        if not tile_type:
            raise ValueError(f"Unknown tile type: {type_id}")
            
        # Copy properties to instance to allow for divergence (e.g. terrain variety)
        self.transparent = tile_type.transparent
        self.walkable = tile_type.walkable
        self.sprites = tile_type.sprites.copy() # Critical: Copy!
        self.color = tile_type.color
        
        # Instance state
        self.visibility_state = VisibilityState.UNEXPLORED
        self.rounds_since_seen = 0
        self.dark = False # Legacy support or move to JSON
```

### Special Logic: Roof Transparency
In `RenderService`, we can leverage the registry or the instance properties to handle occlusion more intelligently.

```python
# In RenderService.render_map (pseudocode)
# Determine occlusion
# ...
tile = map_container.get_tile(x, y, i)
tile_def = TileRegistry.get(tile.type_id)

# "Special Logic": If it's a roof (occludes_below=True) AND we are strictly below it,
# it should block the view (standard occlusion).
# BUT if we want "transparency" when UNDER it, that's a camera/rendering trick.
# Actually, standard occlusion means "If I am at Layer 0, and Layer 1 has a roof, I DON'T see the roof, I see Layer 0 ceiling?"
# No, usually in top-down:
# - If I am at Layer 0 (inside), Layer 1 (roof) should NOT render. (This is currently handled by `render_up_to(player_layer)`).
# - If I am at Layer 0 (outside), Layer 1 (roof of neighbor house) SHOULD render.
# This requires rendering LAYERS ABOVE PLAYER if they are not occluding the PLAYER.
# Current engine only renders `range(base, player_layer + 1)`. 
# To support "seeing roofs of other buildings", we need to render layers > player_layer, 
# but TRANSPARENTLY mask them out if they are strictly above the player.
```

## State of the Art

| Old Approach | Current Approach | Why Change |
|--------------|------------------|------------|
| `Tile(True, False, {...})` | `Tile("floor_stone")` | Removes magic booleans, centralized definition. |
| `if sprite == '#'` | `if not tile.walkable` | Decouples logic from visual representation. |
| Hardcoded `RenderService` colors | Data-driven `color` | Allows varied palettes per tile type. |

## Open Questions

1.  **Rendering Layers Above Player**
    -   **Issue:** Currently, `RenderService` stops at `player_layer`. You cannot see the roof of a house if you are standing outside it on the ground (assuming roof is L1 and ground is L0), because the loop stops at L0.
    -   **Recommendation:** This is a rendering architecture change (Phase 07/08?). For Phase 09, we focus on *defining* the data. The `occludes_below` flag prepares for this future feature.

2.  **Save/Load Migration**
    -   **Issue:** `pickle` saves the `Tile` instance. If `Tile` structure changes, old saves break.
    -   **Recommendation:** Accept that saves will break in this Phase.

## Sources

### Primary (HIGH confidence)
-   `map/tile.py` - Verified current hardcoded structure.
-   `map/map_service.py` - Verified procedural generation modifies sprites.
-   `map/map_generator_utils.py` - Verified dependency on character literals ('#', '.').

### Secondary (MEDIUM confidence)
-   Python `json` documentation - Standard usage.
-   Common Roguelike patterns (Libtcod/TCOD tutorials) - Flyweight pattern for tiles.

## Metadata

**Confidence breakdown:**
-   Standard stack: HIGH (Standard Python)
-   Architecture: HIGH (Proven pattern)
-   Pitfalls: HIGH (Codebase analysis revealed exact issues)

**Research date:** 2024-05-22
**Valid until:** Next major map refactor.
