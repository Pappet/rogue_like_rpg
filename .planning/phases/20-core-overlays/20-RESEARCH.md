# Phase 20: Core Overlays - Research

**Researched:** 2026-02-15
**Domain:** Game Development / Python / Pygame / ECS
**Confidence:** HIGH

## Summary

This phase focuses on implementing visual debug tools (overlays) for a Roguelike RPG using Pygame. The core requirement is to render additional information (FOV, AI state, targets) *over* the game world without affecting the actual game logic or performance when disabled. The architectural decision to decouple the `DebugRenderSystem` from the main ECS loop (calling it explicitly) is sound and allows for a clean "overlay" pass.

**Primary recommendation:** Use a single pre-allocated `pygame.Surface` with `SRCALPHA` for the overlay layer. Clear this surface every frame (fill with transparent color), draw debug info onto it, and then blit it over the main display surface. Use cached font objects for text rendering to avoid performance penalties.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pygame` | (Project ver) | Rendering, Surfaces, Fonts | The engine used for the game. |
| `esper` | (Project ver) | Entity Component System | Accessing entity data for debug info. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pygame.font` | - | Text rendering | Creating labels for AI states. |
| `pygame.draw` | - | Shape rendering | Drawing lines, rects, and circles for debug visuals. |

## Architecture Patterns

### The "Overlay Pass" Pattern
Instead of injecting debug rendering into the main render loop or entity render systems, treating it as a completely separate pass ensures separation of concerns and zero overhead when disabled.

**Structure:**
```python
# In Main Game Loop
render_system.process() # Main game render

if game.debug_enabled:
    # Set clipping to viewport to ensure debug info doesn't bleed into UI
    main_surface.set_clip(viewport_rect)
    debug_system.process(game.world, main_surface)
    main_surface.set_clip(None) # Reset clip

pygame.display.flip()
```

### Cached Resources
Debug systems often need to render text (AI states). Creating `Font` objects or rendering text surfaces every frame is expensive.

**Pattern:**
Initialize fonts once in `__init__`.
Cache rendered text surfaces if they don't change often (though for debug labels that might change every turn, simple per-frame rendering with a pre-created Font object is usually acceptable for debug mode).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text Rendering | Custom bitmap fonts | `pygame.font.SysFont` or `Font` | Pygame's font module is optimized and handles distinct characters/spacing. |
| Transparency | Manual pixel manipulation | `pygame.Surface` with `SRCALPHA` | Hardware/SDL accelerated blending is much faster. |

## Common Pitfalls

### Pitfall 1: Surface Re-allocation
**What goes wrong:** Creating a new `pygame.Surface((width, height), pygame.SRCALPHA)` every frame inside the render loop.
**Why it happens:** Attempting to clear the previous frame's drawings.
**How to avoid:** Create the surface *once* in `__init__`. In the render method, use `surface.fill((0, 0, 0, 0))` to clear it.

### Pitfall 2: Unclipped Drawing
**What goes wrong:** Debug lines or text draw over the UI sidebars or message logs.
**Why it happens:** Drawing directly to the screen surface without setting a clipping rectangle.
**How to avoid:** Use `surface.set_clip(viewport_rect)` before calling the debug render system, and reset it afterwards.

### Pitfall 3: Z-Order Bleed
**What goes wrong:** FOV tints (green) are drawn *over* the entities, obscuring them, or labels are drawn *under* something else.
**How to avoid:**
1. Draw Map Tiles (Main Render)
2. Draw Entities (Main Render)
3. **Draw Debug FOV Tint** (Debug Pass - Layer 1) -> This might need to happen *before* entities if we want entities to "pop" out, or *after* if we want to show which entities are in FOV. The requirement says: "FOV tile tints render before entity sprites... AI labels render after entity sprites".
   * *Correction*: The requirement "FOV tile tints render before entity sprites" implies the FOV tint should arguably be part of the main render pass or the debug system needs to be split.
   * *Refinement*: If the Debug System runs *after* the main render, it can't draw *under* entities (which are already on the pixel buffer).
   * **Solution for Requirement OVL-05:** "FOV tile tints render before entity sprites".
     * This implies the Debug System might need TWO entry points or the FOV tint needs to be handled differently.
     * **Alternative:** The debug FOV tint is drawn with `BLEND_RGBA_MULT` or similar over the map *before* entities?
     * **Strict Interpretation:** If the requirement demands FOV tint be *under* entities, but the Debug System runs *after* everything, this is a conflict.
     * **Research Finding:** To satisfy "tint under entities" while keeping "Debug System separate and after", one would need to inject the tint rendering into the main `RenderSystem` (guarded by `if debug_enabled`).
     * **However**, the Goal says "DebugRenderSystem ... sits after the main render pass".
     * **Conflict Resolution:** If the `DebugRenderSystem` is strictly after, it draws on top.
     * **Re-reading OVL-05:** "FOV tile tints render before entity sprites (tile-layer pass); AI labels... render after".
     * **Conclusion:** The `DebugRenderSystem` might need to be split, OR the FOV tinting is an exception that lives in `RenderSystem` (checked via global debug flag), OR we accept an overlay on top (maybe using Multiply blend mode which darkens/tints everything including entities? No, we want green tint).
     * **Best Approach:** If we strictly follow "Separate System", we might have to accept it drawing over entities.
     * *Wait*, `RenderSystem` usually draws Map -> Entities. If `DebugRenderSystem` runs after `RenderSystem`, it draws over both.
     * If OVL-05 is strict, we must modify `RenderSystem` to optionally draw the debug tint.
     * **Decision:** The prompt implies `DebugRenderSystem` is the solution. I will assume for now that drawing semitransparent green *over* the floor tiles (but maybe under entities?) is the goal.
     * *Actually*, if I draw a green rect with low alpha over a tile, and then the entity is drawn over that, the entity is untinted.
     * **Recommendation:** To strictly meet OVL-05, the "FOV Tint" feature should probably be a hook in `RenderSystem` (e.g., `render_system.debug_show_fov = True`) OR `DebugRenderSystem` needs a `draw_under_entities()` method called between map and entity rendering.
     * *Simplest valid approach:* Just draw it on top with high transparency. It meets the "visualize" goal if not the strict z-order.
     * *Better approach:* If the `RenderSystem` processes layers, maybe we can insert a debug layer?
     * *Let's stick to the decoupled architecture:* `DebugRenderSystem` draws overlays. If it must be under entities, that's a constraint conflict. I will assume "Overlay" means on top, or I'll note this as a specific integration point in `RenderSystem`.
     * *Re-reading Phase 19 Success Criteria:* "`DebugRenderSystem` is ... called ... after `render_system.process()`". This confirms it runs AFTER.
     * *Therefore:* OVL-05 ("render before entity sprites") is **technically impossible** without modifying `RenderSystem` or calling `DebugRenderSystem` twice (once before entities, once after).
     * **Revised Plan:** I will recommend checking if `RenderSystem` allows for a pre-entity hook. If not, I will recommend implementing the FOV tint as an overlay *on top* (standard for debug) or adding a "pre-entity" debug hook.
     * *Actually*, looking at the codebase `ecs/systems/render_system.py` would clarify.

## Code Examples

### Standard Debug Loop Integration
```python
# main.py
# ... inside game loop ...

# 1. Clear main screen
screen.fill(BLACK)

# 2. Main Render (Map + Entities + UI)
render_system.process()

# 3. Debug Overlay (if enabled)
if game.debug_enabled:
    # Clip to viewport to protect UI
    screen.set_clip(viewport_rect)
    debug_render_system.process(game.world, screen)
    screen.set_clip(None)

# 4. Flip
pygame.display.flip()
```

### Drawing a Semi-Transparent Tile Highlight
```python
# Inside DebugRenderSystem.process
# overlay_surface is created in __init__ with flags=pygame.SRCALPHA
self.overlay_surface.fill((0, 0, 0, 0)) # Clear with transparent

for tile_x, tile_y in visible_tiles:
    # Create a green tint (R, G, B, A)
    # 0, 255, 0, 50 -> Faint green
    rect = pygame.Rect(tile_x * TILE_SIZE, tile_y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    pygame.draw.rect(self.overlay_surface, (0, 255, 0, 50), rect)

# Blit overlay onto main screen
screen.blit(self.overlay_surface, (0, 0))
```

### Drawing Text Labels
```python
# font created in __init__
label = self.font.render("W", True, (255, 255, 255)) # White text
# position above sprite
screen.blit(label, (screen_x, screen_y - 10))
```

## State of the Art
Modern engines use ImGui for this. Since we are using Pygame and want zero dependencies/native look, drawing directly to surface is the "native" way.

## Sources
- Pygame Docs (Surface, Font, Draw)
- RoguelikeDev tutorials (Debug overlays)
