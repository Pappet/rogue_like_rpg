# Phase 21: Extended Overlays - Research

**Researched:** 2026-02-15
**Domain:** Debug Rendering / UI
**Confidence:** HIGH

## Summary

This phase enhances the debug overlay system to provide critical information for AI behavior debugging. The current system renders basic AI state labels and chase targets. The extensions will add visual vectors for chase paths, counters for sight loss, and per-NPC FOV cones. A key requirement is the ability to toggle these layers independently.

**Primary recommendation:** Extend `DebugRenderSystem` with dedicated methods for each new overlay type, controlled by a dictionary of flags in `self.persist`, and utilize `VisibilityService` for real-time NPC FOV calculation.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Decoupled DebugRenderSystem from esper:** While other systems are managed by `esper.Processor`, the debug system is called explicitly in the `draw` method. This ensures it always renders on top of everything else and avoids any overhead when disabled, as `esper.process()` would still call it if registered. (2026-02-15)
- **Persistence via `self.persist`:** Storing `debug_enabled` in the state persistence dictionary allows the player to keep the debug view on even when switching to the map and back. (2026-02-15)
- **Overlay Implementation:** Implemented `DebugRenderSystem` methods for FOV, AI labels, and Chase markers, utilizing `pygame.draw` and font rendering directly on a transparent overlay surface. (2026-02-15)
</user_constraints>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pygame` | 2.x | Rendering Lines/Shapes | Existing project standard for 2D graphics. |
| `esper` | 3.x | Entity Component System | Existing ECS framework. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `VisibilityService` | Internal | Shadowcasting | Calculating NPC FOV cones efficiently. |

**Installation:**
No new packages required.

## Architecture Patterns

### Debug Flag Management
Replace the single boolean `debug_enabled` with a dictionary structure in `self.persist` to support granular control.

```python
# In Game.startup / initialization
if "debug_flags" not in self.persist:
    self.persist["debug_flags"] = {
        "master": False,      # Master toggle (F3)
        "player_fov": True,   # Show player's visible tiles
        "npc_fov": True,      # Show NPC vision cones (EXT-03)
        "chase_lines": True,  # Show chase vectors (EXT-01)
        "labels": True        # Show AI state labels (EXT-02)
    }
```

### Pattern 1: On-Demand FOV Calculation
**What:** Calculate NPC FOV only when the debug layer is active and the NPC is on screen.
**When to use:** In `DebugRenderSystem.process` loop.
**Example:**
```python
# Inside DebugRenderSystem loop over NPCs
if self.flags["npc_fov"]:
    visible_tiles = VisibilityService.compute_visibility(
        (pos.x, pos.y), 
        stats.perception, 
        self._get_transparency_func(pos.layer)
    )
    for tx, ty in visible_tiles:
        # Draw tinted rect
```

### Pattern 2: Vector Drawing
**What:** Draw a line from NPC to target with a visual indicator for direction.
**When to use:** For `ChaseData` visualization.
**Example:**
```python
start = (npc_screen_x, npc_screen_y)
end = (target_screen_x, target_screen_y)
pygame.draw.line(surface, COLOR, start, end, 2)
pygame.draw.circle(surface, COLOR, end, 4) # Simple endpoint marker
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| FOV Calculation | Custom raycasting | `VisibilityService.compute_visibility` | Reuse existing, tested shadowcasting logic. |
| Text Rendering | Custom bitmap fonts | `pygame.font.Font` | Native Pygame font rendering is sufficient and faster to implement. |

**Key insight:** The `VisibilityService` is stateless (static methods), making it perfect for use in `DebugRenderSystem` without coupling to `VisibilitySystem` state.

## Common Pitfalls

### Pitfall 1: Transparency Logic Duplication
**What goes wrong:** `DebugRenderSystem` might use different transparency rules than `AISystem`, leading to confusing debug info (e.g., NPC "sees" through a wall in debug but not in logic).
**Why it happens:** Hardcoding `is_transparent` checks in multiple places.
**How to avoid:** Ensure `DebugRenderSystem` uses the exact same transparency logic (e.g., checking `tile.transparent` AND `tile.sprites` if necessary, matching `AISystem`'s implementation).

### Pitfall 2: Coordinate Space Confusion
**What goes wrong:** Drawing debug shapes in world coordinates instead of screen coordinates (camera offset).
**Why it happens:** Forgetting to subtract `self.camera.x` / `self.camera.y`.
**How to avoid:** Always apply camera offset transform before drawing to `self.overlay`.

### Pitfall 3: Performance with Many NPCs
**What goes wrong:** Calculating FOV for every NPC on the map drops FPS.
**Why it happens:** Shadowcasting is expensive if done 50+ times per frame.
**How to avoid:** Only calculate FOV for NPCs whose *positions* are within the camera viewport.

## Code Examples

### EXT-03: NPC FOV Visualization
```python
# ecs/systems/debug_render_system.py

def _render_npc_fov(self):
    if not self.flags.get("npc_fov"):
        return

    for ent, (pos, stats, ai_state) in esper.get_components(Position, Stats, AIBehaviorState):
        # Optimization: Cull off-screen NPCs
        if not self.camera.contains(pos.x, pos.y):
            continue

        # Use shared transparency logic
        def is_transparent(x, y):
             tile = self.map_container.get_tile(x, y, pos.layer)
             # Match AISystem logic exactly
             return tile and tile.transparent and tile.sprites.get(SpriteLayer.GROUND) != "#"

        visible = VisibilityService.compute_visibility(
            (pos.x, pos.y), 
            stats.perception, 
            is_transparent
        )

        for vx, vy in visible:
            # Convert to screen coords
            sx, sy = self.camera.apply(vx, vy)
            # Draw tint
            s = pygame.Surface((self.TILE_SIZE, self.TILE_SIZE), pygame.SRCALPHA)
            s.fill((255, 0, 0, 30)) # Red tint for enemies
            self.overlay.blit(s, (sx, sy))
```

### EXT-01: Chase Vectors
```python
# ecs/systems/debug_render_system.py

def _render_chase_vectors(self):
    if not self.flags.get("chase_lines"):
        return

    for ent, (pos, chase, ai) in esper.get_components(Position, ChaseData, AIBehaviorState):
        if ai.state == AIState.CHASE:
            start_pos = (
                pos.x * TILE_SIZE - self.camera.x + TILE_SIZE // 2, 
                pos.y * TILE_SIZE - self.camera.y + TILE_SIZE // 2
            )
            end_pos = (
                chase.last_known_x * TILE_SIZE - self.camera.x + TILE_SIZE // 2,
                chase.last_known_y * TILE_SIZE - self.camera.y + TILE_SIZE // 2
            )
            
            pygame.draw.line(self.overlay, DEBUG_CHASE_COLOR, start_pos, end_pos, 2)
            pygame.draw.circle(self.overlay, DEBUG_CHASE_COLOR, end_pos, 4)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global `debug_enabled` bool | `debug_flags` Dictionary | Phase 21 | Allows granular control of visual noise. |
| Rect for Target | Vector Line | Phase 21 | Shows direction and path clearly. |
| No NPC FOV | Real-time Shadowcast | Phase 21 | Visually confirms why NPC noticed player. |

## Open Questions

1.  **Toggle Input Mapping:**
    -   What keys to use for individual toggles?
    -   Recommendation: Use `Shift+F3` to cycle modes or `F4-F8` for individual toggles if `F3` (Master) is on. Simplest is: F3 = Master, 1-4 = Toggles (only when Master is ON).

## Sources

### Primary (HIGH confidence)
- `ecs/systems/debug_render_system.py` - Current implementation analysis.
- `ecs/systems/ai_system.py` - AI transparency and logic.
- `services/visibility_service.py` - Shadowcasting API.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Core libraries are established.
- Architecture: HIGH - Pattern is simple extension of existing system.
- Pitfalls: MEDIUM - Performance impact of multiple FOV casts is the main risk.

**Research date:** 2026-02-15
**Valid until:** Phase 22 (Refinement)
