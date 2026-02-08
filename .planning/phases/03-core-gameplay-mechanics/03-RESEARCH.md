# Phase 3: Core Gameplay Mechanics - Research

**Researched:** 2024-05-23
**Domain:** Rogue-like Mechanics (ECS, LoS/FoW, UI Layout, Targeting)
**Confidence:** HIGH

## Summary

This phase involves transitioning the existing object-oriented architecture to an **Entity Component System (ECS)** using the `esper` library. This shift allows for more flexible interactions between entities and systems. Key gameplay improvements include a sophisticated **4-state Fog of War** (Visible, Shrouded, Forgotten, Unexplored) and an efficient **Recursive Shadowcasting** Line of Sight (LoS) algorithm. The UI will be restructured to feature persistent headers and sidebars, and a robust **Targeting System** will support both entity cycling and manual AoE/Beam placement.

**Primary recommendation:** Use the `esper` library for ECS and implement recursive shadowcasting for LoS to ensure performance and visual accuracy.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Core Decision:** The existing object-oriented services (Party, Turn, Map) will be refactored into an **Entity Component System (ECS)** pattern to handle complex interactions between heroes, enemies, and effects.
- **Entities:** Heroes, Enemies, Items, Traps, and Special Effects.
- **Components:** `Position`, `Renderable`, `Stats` (HP, Mana, Perception, Intelligence), `Inventory`, `TurnOrder`, `LightSource`.
- **Systems:** `MovementSystem`, `TurnSystem`, `RenderSystem`, `VisibilitySystem` (FoW), `ActionSystem`.
- **Visibility States:**
    1. **Visible:** Currently within sight range and Line of Sight (LoS).
    2. **Hidden (Shroud):** Previously explored, currently out of sight. Rendered with the original tile sprite but tinted grey.
    3. **Forgotten:** Explored in the past, but the party has "forgotten" the details. Represented by a unique "Forgotten" sprite (e.g., vage outlines). Triggers upon leaving the Map Container.
    4. **Unexplored:** Completely unknown. Rendered with a solid black/unexplored sprite.
- **Logic:**
    - **Sigh Range:** Based on the maximum `Perception` attribute of active (living) party members.
    - **Line of Sight:** Walls and obstacles block visibility.
    - **Memory Logic:** When leaving a container, tiles are "forgotten" based on a calculation of elapsed rounds and the maximum `Intelligence` of the party.
- **Turn Header:** A fixed UI header displaying the global round counter and current turn status ("Player Turn" vs. "Environment Turn").
- **Action List:** A permanently visible sidebar listing available actions (Move, Investigate, Ranged, Spells, Items). 
    - Actions that are unavailable (e.g., no mana for spells, no arrows for ranged) are greyed out and skipped during navigation.
- **Action Flow:** `Select Action from List` -> `Select Target (if required)` -> `Confirm`.
- **Modes:**
    - **Normal/Aggressive:** Bump-to-attack or move.
    - **Investigation:** Move cursor to a specific tile (LoS applies). High-level skills might check a radius (e.g., 3x3).
    - **Ranged/Spells:** 
        - Uses **Auto-Targeting** for entities: The cursor cycles through valid targets (enemies/allies) within range and LoS.
        - Uses **Manual Target** for area effects: Cursor moves freely within max range.

### Claude's Discretion
- Implementation details for the "Forgotten" state logic.
- Choice of ECS library (recommended `esper`).
- Specific Line of Sight algorithm (recommended Shadowcasting).
- UI layout implementation details in Pygame.

### Deferred Ideas (OUT OF SCOPE)
- No audio feedback for turn changes.
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **esper** | 3.x | ECS Framework | Lightweight, dependency-free, high performance, popular in Python rogue-like community. |
| **pygame** | 2.x | Engine/Rendering | Project base. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **numpy** | 1.2x | FOV Optimization | Use if Python loops for Shadowcasting become a bottleneck (optional). |

## Architecture Patterns

### Recommended Project Structure
```
src/
├── components/      # Data classes (Stats, Position, Renderable)
├── systems/         # Logic (MovementSystem, VisibilitySystem, RenderSystem)
├── ui/              # UI Layout and Elements
└── core/
    └── ecs_world.py # Central esper.World instance
```

### Pattern 1: Event-Driven System Communication
**What:** Use `esper.dispatch` for UI-to-World communication.
**When to use:** When a user selects an action or target in the UI.
**Example:**
```python
# UI Layer
def on_action_click(action_id):
    esper.dispatch("action_selected", action_id)

# ActionSystem (Processor)
class ActionSystem(esper.Processor):
    def __init__(self):
        esper.set_handler("action_selected", self.handle_action)

    def handle_action(self, action_id):
        # Update world state / targeting mode
        pass
```

### Anti-Patterns to Avoid
- **System Bloat:** Putting non-related logic in a single System (e.g., mixing Render and Physics).
- **Hard-coded Layouts:** Don't use absolute pixel coordinates without `Rect` containers for UI.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ECS Core | Custom registry | `esper` | Handles entity IDs and component mapping efficiently. |
| Basic UI Widgets | Custom button logic | `pygame-gui` (optional) or simplified Rect-based wrapper | Complex UI interactions (scrolling, text wrapping) are hard to get right. |

## Common Pitfalls

### Pitfall 1: O(N) Visibility Checks
**What goes wrong:** Checking every tile for visibility every frame.
**Why it happens:** Inefficient algorithms or lack of caching.
**How to avoid:** Use Recursive Shadowcasting (processes each tile once) and only update when the player moves.

### Pitfall 2: ECS Synchronization
**What goes wrong:** Updating components in a way that systems see inconsistent states.
**Why it happens:** Modifying the world while iterating.
**How to avoid:** `esper` handles this, but avoid adding/removing components inside a `world.get_components` loop if possible; use command queues if needed.

## Code Examples

### Recursive Shadowcasting (Pattern)
```python
def compute_fov(origin, radius):
    # Process 8 octants
    for octant in range(8):
        scan(octant, origin, radius, 1, 0, 1)

def scan(octant, origin, radius, row, start_slope, end_slope):
    if start_slope < end_slope: return
    # Iterate through tiles in the row
    # Adjust slopes based on blocked tiles (walls)
    # Recursively call scan for next row
```

### 4-State FoW Render Logic
```python
def render_tile(tile, state):
    if state == VISIBLE:
        screen.blit(tile.sprite, pos)
    elif state == SHROUDED:
        screen.blit(tile.sprite, pos)
        screen.blit(grey_overlay, pos) # Tinted grey
    elif state == FORGOTTEN:
        screen.blit(vague_outline_sprite, pos)
    elif state == UNEXPLORED:
        screen.blit(black_sprite, pos)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Raycasting | Shadowcasting | More accurate "shadows", better performance for 2D grids. |
| Service-based OO | ECS | Decoupled logic, easier to add "status effects" as components. |

## Open Questions

1. **Memory Decay Constant (K):** What is the ideal value for `max_intel * K`?
   - Recommendation: Start with `K = 10` (e.g., 15 Intel = 150 rounds).
2. **AoE Visuals:** Best way to render radius/beams in Pygame?
   - Recommendation: Use a transparent surface with `pygame.draw.circle` or `polygon` for the area, then blit with `SRC_ALPHA`.

## Sources

### Primary (HIGH confidence)
- [esper PyPI](https://pypi.org/project/esper/) - ECS Documentation
- [Recursive Shadowcasting - RogueBasin](http://www.roguebasin.com/index.php/Recursive_Shadowcasting) - FOV Algorithm
- [Pygame Docs](https://www.pygame.org/docs/) - UI/Rect management

### Secondary (MEDIUM confidence)
- [ECS for Roguelikes - Reddit/Gamedev](https://www.reddit.com/r/roguelikedev/) - Community patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `esper` is stable and fits well.
- Architecture: HIGH - ECS is well-documented for this genre.
- Pitfalls: MEDIUM - Dependent on specific implementation details.

**Research date:** 2024-05-23
**Valid until:** 2024-06-23
