# Phase 28: Day/Night Visual Cycle - Research

**Researched:** 2026-02-16
**Domain:** Graphics (PyGame), ECS (Esper), World Simulation
**Confidence:** HIGH

## Summary

This phase implements the visual and mechanical effects of the passage of time. It translates the `WorldClockService` phase (DAWN, DAY, DUSK, NIGHT) into a global visual atmosphere and modifies player capabilities (specifically FOV radius). 

The primary technical challenge is implementing an efficient full-screen (or viewport) tint in PyGame and ensuring that the ECS systems (Stats and Visibility) react correctly and immediately to time-of-day changes.

**Primary recommendation:** Use a semi-transparent overlay surface for efficient full-viewport tinting and implement a `StatsSystem` (or update the existing `EquipmentSystem`) that updates `EffectiveStats` with time-based multipliers before the `VisibilitySystem` runs.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGame | 2.x | Rendering & Input | Core game engine |
| Esper | 3.x | ECS Framework | Core architecture |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python Standard | 3.10+ | Math & Logic | Interpolation and logic |

**Installation:**
Already installed as part of the core stack.

## Architecture Patterns

### Recommended Project Structure
- No new directories required. 
- Updates to `services/render_service.py` to handle viewport tinting.
- Updates to `ecs/systems/` to include or rename `EquipmentSystem` to `StatsSystem`.
- New constants in `config.py`.

### Pattern 1: Viewport Tinting Overlay
**What:** Create a persistent `pygame.Surface` with the same dimensions as the viewport, initialized with `pygame.SRCALPHA`.
**When to use:** In the `draw` loop, after rendering the map and entities but before rendering the UI.
**Example:**
```python
# Create surface (once or on resize)
tint_surface = pygame.Surface((viewport_width, viewport_height), pygame.SRCALPHA)

# In draw loop:
# Alpha is derived from Ambient Light Multiplier: alpha = (1.0 - multiplier) * 255
tint_color = (0, 0, 40, 120) # Night: Dark Blue with alpha
tint_surface.fill(tint_color)
surface.blit(tint_surface, (viewport_x, viewport_y))
```

### Pattern 2: Effective Stats Pipeline
**What:** A system that recalculates `EffectiveStats` from `Stats` + `Equipment` + `Environment`.
**When to use:** Must run *after* the clock advances and *before* systems that depend on stats (like `VisibilitySystem` or `CombatSystem`).
**Priority:** High (should run early in `esper.process()`).

### Anti-Patterns to Avoid
- **Per-Pixel Manipulation:** Don't iterate over pixels to darken the screen; it's extremely slow in Python/PyGame.
- **Modifying Base Stats:** Never change `Stats.perception` directly based on time. Always use `EffectiveStats`.
- **Stat Cache Invalidation:** Avoid using cached FOV results if the time of day has changed; recalculate FOV every turn (which the current `VisibilitySystem` already does).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Screen Tinting | Custom pixel shaders | `pygame.Surface` blit | Highly optimized in PyGame/SDL. |
| Time Logic | Custom hour/minute math | `WorldClockService` | Already implemented and centralizes time. |
| Color Blending | Custom RGBA math | `surface.fill((R,G,B,A))` | Native SDL implementation is faster and handles alpha correctly. |

## Common Pitfalls

### Pitfall 1: Stale Visibility
**What goes wrong:** FOV radius doesn't update immediately when the phase transitions (e.g., from DAY to NIGHT).
**Why it happens:** `VisibilitySystem` runs before the `StatsSystem` updates the perception multiplier, or before the `TurnSystem` advances the clock.
**How to avoid:** Reorder processors in `Game.startup`: `TurnSystem` -> `StatsSystem` -> `VisibilitySystem`.

### Pitfall 2: UI Darkening
**What goes wrong:** The message log, sidebar, or health bars become dark and unreadable at night.
**Why it happens:** Applying the tint to the entire screen surface instead of just the game viewport.
**How to avoid:** Use `surface.set_clip(viewport_rect)` or blit the tint only to the viewport coordinates.

### Pitfall 3: Perception Floor
**What goes wrong:** FOV radius becomes 0 or negative, causing errors in visibility calculations or rendering.
**Why it happens:** Multiplier (e.g., 0.5x) applied to low base perception (e.g., 1) resulting in 0.5 -> 0.
**How to avoid:** Use `max(1, int(perception * multiplier))` to ensure at least the current tile is visible.

## Code Examples

### Calculating Tint and Multiplier with Smooth Transitions
```python
# In config.py
DN_SETTINGS = {
    "day":   {"tint": (0, 0, 0),     "light": 1.0, "perception": 1.0},
    "dawn":  {"tint": (255, 200, 150), "light": 0.8, "perception": 0.8},
    "dusk":  {"tint": (150, 100, 200), "light": 0.7, "perception": 0.7},
    "night": {"tint": (0, 0, 40),     "light": 0.4, "perception": 0.5},
}

# Example of interpolation logic (if needed for "smooth" transitions)
def get_current_dn_stats(clock_state):
    phase = clock_state["phase"]
    # For now, discrete phase is enough, but can interpolate here
    settings = DN_SETTINGS[phase]
    alpha = int((1.0 - settings["light"]) * 255)
    return settings["tint"] + (alpha,), settings["perception"]
```

### Updated VisibilitySystem Logic (Conceptual)
```python
class VisibilitySystem(esper.Processor):
    def process(self):
        # ... existing logic ...
        for ent, (pos, stats) in esper.get_components(Position, Stats):
            # Use EffectiveStats if available, otherwise fallback to base Stats
            eff_perception = stats.perception
            if esper.has_component(ent, EffectiveStats):
                eff_perception = esper.component_for_entity(ent, EffectiveStats).perception
            
            radius = eff_perception
            # Apply LightSource if present (LightSources are not affected by time of day)
            if esper.has_component(ent, LightSource):
                radius = max(radius, esper.component_for_entity(ent, LightSource).radius)
            # ... compute visibility ...
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Stats.perception` | `EffectiveStats.perception` | Phase 25/28 | Decouples base stats from temporary modifiers. |
| Global darkened sprites | Tint Overlay | Standard practice | Easier to adjust and supports colored lighting. |

## Open Questions

1. **Interpolation:** Should transitions be perfectly smooth (per tick) or per-phase?
   - *Recommendation:* Start with per-phase. If "smoothness" is a hard requirement, interpolate the Alpha of the tint surface and the perception multiplier based on minutes within the transition hour.
2. **Indoor Maps:** Do dungeons have a day/night cycle?
   - *Recommendation:* For now, yes (global). Later, add an `is_outdoors` attribute to `MapContainer` to bypass the environmental perception penalty and tint.

## Sources

### Primary (HIGH confidence)
- PyGame Documentation: `Surface.blit`, `SRCALPHA`, `Surface.fill`.
- Existing Codebase: `services/world_clock_service.py`, `ecs/systems/equipment_system.py`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Core project technology.
- Architecture: HIGH - Standard PyGame patterns for rogue-likes.
- Pitfalls: HIGH - Common issues in ECS-based turn games.

**Research date:** 2026-02-16
**Valid until:** 2026-03-16
