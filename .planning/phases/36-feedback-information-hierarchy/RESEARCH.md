# Phase 36: Feedback & Information Hierarchy - Research

**Researched:** 2026-02-14
**Domain:** UI/UX, Information Architecture, Floating Combat Text (FCT)
**Confidence:** HIGH

## Summary

This phase focuses on enhancing player immersion and information transparency through dynamic feedback systems. The primary challenges are managing the lifecycle of ephemeral UI elements (Floating Combat Text) in an ECS architecture and creating a clear information hierarchy using color-coded logging and an "Examine" mode.

**Primary recommendation:** Use Esper entities for Floating Combat Text with short lifespans (TTL) and vertical pixel-offset movement. Implement a dedicated `ExamineState` that leverages the existing `UIStack` to display tooltips for entities under the cursor.

## User Constraints

No `CONTEXT.md` provided; following phase requirements (FEED-01 to FEED-04).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Esper | 3.x+ | Entity Component System | Existing core for state management |
| Pygame | 1.x+ | Graphics Rendering | Existing core for drawing and font handling |

### Supporting
| Component | Purpose | Data Fields |
|-----------|---------|-------------|
| `FCT` | Floating Text Data | `text`, `color`, `vx`, `vy`, `ttl`, `max_ttl`, `offset_y` |
| `Tooltip` | Hover Info | `header`, `lines`, `icon_sprite`, `follow_cursor` |

## Architecture Patterns

### Recommended Project Structure
```
ui/
├── windows/
│   ├── tooltip.py       # New: Lightweight window for "Examine" info
│   └── examine.py       # New: Logic for the examine cursor and modal trigger
ecs/
├── systems/
│   ├── fct_system.py    # New: Updates TTL, movement, and alpha of FCT entities
│   └── tooltip_system.py # New: Manages tooltip visibility and content mapping
```

### Pattern 1: FCT Lifecycle in ECS
**What:** Use standard Esper entities for FCT instead of a custom list inside a system.
**When to use:** For any short-lived text that needs to move or fade (damage, "Miss!", status gains).
**Implementation:**
- **Spawn:** `spawn_fct(x, y, text, color, vx=0, vy=-1.5, ttl=1.0)`
- **Update:** `pos.y += vy * dt`, `ttl -= dt`, `alpha = (ttl/max_ttl) * 255`.
- **Cleanup:** `world.delete_entity(entity)` when `ttl <= 0`.

### Pattern 2: Log Categorization with Enums
**What:** Define a `LogCategory` enum to decouple game logic from UI colors.
**Why:** Prevents hardcoding `(255, 50, 50)` every time damage is dealt.
**Example:**
```python
class LogCategory(Enum):
    GENERAL = auto()
    DAMAGE_DEALT = auto()
    DAMAGE_RECEIVED = auto()
    HEALING = auto()
    SYSTEM = auto()

LOG_COLORS = {
    LogCategory.DAMAGE_DEALT: (100, 255, 100), # Green
    LogCategory.DAMAGE_RECEIVED: (255, 100, 100), # Red
    # ...
}
```

### Anti-Patterns to Avoid
- **Tile-Locked FCT:** Don't snap FCT to the 32px grid. It should move in smooth pixel increments (using a `ScreenPosition` or `offset_y` field) for better visual juice.
- **Message Log Overload:** Don't render the entire history every frame. Use a `Dirty` flag or render to a cached surface.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Easing/Tweening | Complex Engine | Simple Math | `alpha = max(0, int(255 * (ttl / max_ttl)))` is sufficient. |
| Text Wrapping | Custom Word Split | Standard Helper | Use a font-aware wrapping loop (see Code Examples). |
| Rich Text | Full Markdown Parser | Existing `parse_rich_text` | Current regex solution is enough for [color] tags. |

## Common Pitfalls

### Pitfall 1: FCT Clumping
**What goes wrong:** Multiple hits in one frame stack perfectly, making them unreadable.
**How to avoid:** Add random horizontal jitter (`vx = random.uniform(-0.5, 0.5)`) to each spawn.

### Pitfall 2: Tooltip Occlusion
**What goes wrong:** The tooltip box appears over the player/cursor, hiding what the user is examining.
**How to avoid:** Calculate tooltip rect and offset it (e.g., 20px right and 20px up) from the cursor.

### Pitfall 3: Screen Edge Clipping
**What goes wrong:** Tooltips for entities at the right or top edge of the screen are cut off.
**How to avoid:** Check `tooltip_rect.right > SCREEN_WIDTH` and `tooltip_rect.top < 0`, then shift the rect left/down accordingly.

## Code Examples

### Simple Word Wrapping Helper
```python
def wrap_text(text, font, max_width):
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        width, _ = font.size(test_line)
        if width <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines
```

### FCT System (Esper)
```python
class FCTSystem(esper.Processor):
    def process(self, dt):
        for entity, (pos, fct) in self.world.get_components(Position, FCT):
            # Move (smooth pixel offset)
            fct.offset_y += fct.vy * dt * 60
            fct.offset_x += fct.vx * dt * 60
            
            # Fade
            fct.ttl -= dt
            if fct.ttl <= 0:
                self.world.delete_entity(entity)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Message log prints to console | Color-coded rich text log | Better visibility of status/threats |
| "What is this?" requires wiki | "Examine" mode tooltips | Reduced cognitive load, faster play |

## Open Questions

1. **Mouse Support:** Should "Examine" mode work on mouse-hover as well?
   - *Recommendation:* Current game is primary keyboard, but mouse-hover tooltips are expected in 1280x720 windowed games. Support both.
2. **Animation Overlap:** Should FCT block other animations?
   - *Recommendation:* No, FCT is asynchronous feedback.

## Sources

### Primary (HIGH confidence)
- `esper` Documentation - ECS system patterns.
- `pygame.font` Documentation - Width measurement and surface rendering.

### Secondary (MEDIUM confidence)
- RoguelikeDev "Juice" threads (Reddit/Blogs) - FCT jitter and vertical float patterns.

## Metadata
**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: HIGH

**Research date:** 2026-02-14
**Valid until:** 2026-03-14
