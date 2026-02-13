# Phase 6: Advanced Navigation & UI - Research

**Researched:** 2024-05-24
**Domain:** Map Memory, Aging & UI
**Confidence:** HIGH

## Summary

This phase focuses on two advanced navigation features: **Active Map Memory** (maps "age" and degrade over time when inactive) and a **World Map UI** (a global or local overview of discovered areas).

The core technical challenge is implementing "inactive aging" without running simulation on inactive maps. The recommended approach is **Lazy Evaluation**: record the timestamp (turn) when leaving a map, and calculate the decay when returning.

For the UI, a new **World Map State** is recommended, which renders a scaled-down "minimap" of the current `MapContainer`. This requires persisting the `TurnSystem` state to maintain a global clock across map transitions.

**Primary recommendation:** Implement `MapContainer.on_exit()` and `on_enter()` hooks to handle lazy aging, and create a modal `WorldMapState` for the UI.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `MapContainer` | Internal | Map State | Stores tile data and visibility states. |
| `VisibilitySystem` | Internal | Active Aging | Handles line-of-sight and memory decay while map is active. |
| `Pygame` | 2.x | UI Rendering | Standard drawing primitives (`draw.rect`) for the minimap. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `GameStates` | Internal | State Mgmt | To toggle between "Game" and "WorldMap" modes. |
| `TurnSystem` | Internal | Timekeeping | Provides the global `round_counter` for aging calculations. |

## Architecture Patterns

### Lazy Map Aging
Instead of simulating inactive maps, we calculate the delta upon return.

1.  **On Exit:** `last_visited_round = global_round_counter`. Mark all `VISIBLE` tiles as `SHROUDED`.
2.  **On Enter:** `turns_passed = global_round_counter - last_visited_round`.
3.  **Process:** Iterate all tiles. If `SHROUDED`, `rounds_since_seen += turns_passed`.
4.  **Decay:** If `rounds_since_seen > threshold`, transition to `FORGOTTEN`.

### Intelligence-Based Memory
The memory threshold is derived from the player's stats, consistent between active and inactive states.

```python
# Formula
memory_threshold = player_intelligence * 5  # e.g., 10 INT = 50 turns memory
```

### World Map Modal
A dedicated Game State that pauses the game and renders the map.

```python
class WorldMapState(GameState):
    def startup(self, persist):
        # Generate map surface once on entry
        self.map_surface = self.generate_minimap(persist['map_container'])
    
    def draw(self, screen):
        screen.blit(self.map_surface, centered_rect)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Minimap Scaling | Custom Pixel Manipulation | `pygame.draw.rect` | Drawing small rects is faster and easier than scaling a massive texture. |
| State Switching | Custom UI Flags | `GameState` Stack/Switch | Keep the main loop clean; don't clutter `Game.update` with UI logic. |
| Time Tracking | Custom Map Clock | `TurnSystem.round_counter` | Use the single source of truth for time. |

**Key insight:** The "World Map" is just a visualization of the existing `MapContainer` data. No new data structure is needed for the map itself, only for the *rendering* logic (colors/scale).

## Common Pitfalls

### Pitfall 1: Turn Counter Reset
**What goes wrong:** Leaving `Game` state to `WorldMap` and returning resets `TurnSystem` (and `round_counter` becomes 1).
**Why it happens:** `Game.startup()` often re-initializes systems `self.turn_system = TurnSystem()`.
**How to avoid:** Persist `TurnSystem` (or just the `round_counter`) in the `persist` dictionary passed between states.

### Pitfall 2: Visible Tiles on Exit
**What goes wrong:** Player leaves map, returns, and tiles are still `VISIBLE` (bright), implying they can see them from a different map.
**Why it happens:** `VISIBLE` state isn't cleared on exit.
**How to avoid:** In `MapContainer.on_exit()`, explicitly downgrade all `VISIBLE` tiles to `SHROUDED`.

### Pitfall 3: Inconsistent Aging
**What goes wrong:** Maps age differently when active vs. inactive.
**Why it happens:** Logic duplicated between `VisibilitySystem` (active) and `MapContainer` (inactive restoration).
**How to avoid:** Use a shared constant or method for the `memory_threshold` calculation. Ensure `rounds_since_seen` is updated in both places.

## Code Examples

### Map Aging Logic
```python
# In MapContainer
def on_exit(self, current_round: int):
    self.last_visited_round = current_round
    # Downgrade visible to shrouded
    for layer in self.layers:
        for row in layer.tiles:
            for tile in row:
                if tile.visibility_state == VisibilityState.VISIBLE:
                    tile.visibility_state = VisibilityState.SHROUDED
                    tile.rounds_since_seen = 0

def on_enter(self, current_round: int, memory_threshold: int):
    if self.last_visited_round is None:
        return
        
    turns_passed = current_round - self.last_visited_round
    if turns_passed <= 0:
        return

    # Apply aging
    for layer in self.layers:
        for row in layer.tiles:
            for tile in row:
                if tile.visibility_state == VisibilityState.SHROUDED:
                    tile.rounds_since_seen += turns_passed
                    if tile.rounds_since_seen > memory_threshold:
                        tile.visibility_state = VisibilityState.FORGOTTEN
```

### World Map Rendering (Minimap)
```python
def generate_minimap(self, map_container):
    scale = 4 # 4x4 pixels per tile
    w = map_container.width * scale
    h = map_container.height * scale
    surface = pygame.Surface((w, h))
    
    for y in range(map_container.height):
        for x in range(map_container.width):
            tile = map_container.get_tile(x, y)
            color = (0, 0, 0) # UNEXPLORED
            
            if tile.visibility_state == VisibilityState.VISIBLE:
                color = (200, 200, 200)
            elif tile.visibility_state == VisibilityState.SHROUDED:
                color = (100, 100, 100)
            elif tile.visibility_state == VisibilityState.FORGOTTEN:
                color = (50, 50, 60)
                
            if tile.visibility_state != VisibilityState.UNEXPLORED:
                pygame.draw.rect(surface, color, (x*scale, y*scale, scale, scale))
                
    return surface
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `forget_all()` | Lazy Aging | Phase 6 | Maps retain history but degrade naturally. |
| No World Map | Modal UI | Phase 6 | Players can orient themselves in larger dungeons. |

**Deprecated/outdated:**
- **Immediate Forgetting:** The `forget_all` method calling `tile.visibility_state = FORGOTTEN` immediately is now incorrect.

## Open Questions

1.  **Landmark Persistence**
    - What we know: `FORGOTTEN` tiles are dark. Entities (stairs) are removed on freeze.
    - What's unclear: Should the World Map show "Known Stairs" even if the tile is FORGOTTEN?
    - Recommendation: For Phase 6, stick to tile visibility. If you forget the room, you forget the stairs. A "Note/Marker" system could be a future enhancement.

2.  **Parent Map Visualization**
    - What we know: Goal mentions "parent containers".
    - What's unclear: How to visualize the connection.
    - Recommendation: Start with the *current* map view. "Parent" view implies a region map, which might just be a different `MapContainer` (e.g., City Map). If the player is in a House, the "World Map" might logically be the City Map, but technically we usually show the *interior* map first.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Pygame/ECS standard.
- Architecture: HIGH - Lazy evaluation is standard for this problem.
- Pitfalls: MEDIUM - State persistence issues are tricky in this custom engine.

**Research date:** 2024-05-24
**Valid until:** Phase 7
