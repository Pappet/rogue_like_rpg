# Phase 19: Debug Infrastructure - Research

**Researched:** 2026-02-15
**Domain:** Game Engine Tooling / Rendering Pipeline
**Confidence:** HIGH

## Summary

This phase establishes the foundation for visual debugging tools. The primary goal is to inject a debug rendering pass into the existing game loop without affecting performance when disabled. The system will use a dedicated `DebugRenderSystem` that draws to a pre-allocated `SRCALPHA` surface, overlaid on the game view.

**Primary recommendation:** Implement `DebugRenderSystem` following the existing `RenderSystem` pattern (explicit call, no `esper` registration), controlled by a boolean flag in `Game.persist`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pygame` | 2.x | Graphics/Input | Core engine used by project |
| `esper` | 3.x | ECS | Entity management used by project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `config` | Local | Constants | Screen dims, colors, layer defs |

## Architecture Patterns

### Debug System Integration
**What:** Explicitly called rendering system.
**When to use:** For rendering passes that need precise ordering (e.g., after entities, before UI) and aren't subject to standard ECS processing rules (like pausing).
**Example:**
```python
# In Game.draw()
if self.persist.get("debug_enabled"):
    self.debug_render_system.process(surface)
```

### Toggle Persistence
**What:** Store debug state in the `persist` dictionary passed between states.
**Why:** Ensures debug mode stays on when switching between Map and Game states, or reloading.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Transparency | Manual pixel manipulation | `pygame.SRCALPHA` | Hardware accelerated (mostly), cleaner API |
| Input Handling | Custom event polling | `pygame.event` + `Game.get_event` | Consistent with existing input flow |

## Common Pitfalls

### Pitfall 1: Allocation in Loop
**What goes wrong:** Creating new `pygame.Surface` or `Font` objects inside `process()`.
**Why it happens:** Convenience ("I just need a surface for this rect").
**How to avoid:** Create `self.overlay` and `self.font` in `__init__`. Clear overlay with `fill((0,0,0,0))` each frame.
**Warning signs:** Frame rate drops when debug is enabled (or disabled if check is wrong).

### Pitfall 2: Coordinate Space Confusion
**What goes wrong:** Drawing debug info at screen coordinates instead of world coordinates (or vice versa).
**How to avoid:** Use `self.camera.apply_to_pos(x, y)` for world-to-screen conversion, just like `RenderSystem`.

## Code Examples

### DebugRenderSystem Skeleton
```python
class DebugRenderSystem:
    def __init__(self, camera):
        self.camera = camera
        # Pre-allocate overlay surface
        self.overlay = pygame.Surface((camera.width, camera.height), pygame.SRCALPHA)
        self.font = pygame.font.SysFont("monospace", 12)

    def process(self, surface):
        # 1. Clear overlay
        self.overlay.fill((0, 0, 0, 0))
        
        # 2. Draw debug info (example)
        # ... drawing code here ...

        # 3. Blit overlay to main surface
        # Assuming surface is already clipped to viewport
        surface.blit(self.overlay, (self.camera.offset_x, self.camera.offset_y))
```

### Input Toggle
```python
# In Game.handle_player_input
if event.key == pygame.K_F3:
    current = self.persist.get("debug_enabled", False)
    self.persist["debug_enabled"] = not current
    print(f"Debug mode: {self.persist['debug_enabled']}")
```

## Sources

### Primary (HIGH confidence)
- `ecs/systems/render_system.py` - Verified existing explicit-call pattern.
- `game_states.py` - Verified `persist` dict usage and `draw` loop structure.
- `main.py` - Verified initialization and main loop.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Existing project structure is clear.
- Architecture: HIGH - Follows established patterns.
- Pitfalls: HIGH - Standard Pygame performance issues.

**Research date:** 2026-02-15
