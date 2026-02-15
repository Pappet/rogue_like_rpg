# Phase 22: Debug System Refinement - Research

**Researched:** 2024-05-23
**Domain:** UI/Debugging, ECS, Map Transitions
**Confidence:** HIGH

## Summary

This phase addresses critical stale-data issues and logic inconsistencies in the `DebugRenderSystem`. Currently, the debug system does not update its map reference when the player transitions between maps, leading to incorrect visualizations (e.g., seeing the old map's FOV while in a new village). Furthermore, the transparency logic used for NPC FOV visualization does not account for the `#` wall fallback used by the `AISystem` and `VisibilitySystem`, causing a discrepancy between what the debug overlay shows and what the NPC actually "sees." Finally, existing verification tests are broken due to signature mismatches in the `process` method.

**Primary recommendation:** Introduce a `set_map` method to `DebugRenderSystem`, update its `process` signature to include `player_layer`, and align its transparency logic with the core visibility systems.

## User Constraints

> [!NOTE]
> This phase is a gap closure phase based on the v1.3 audit.

### Locked Decisions
- Fix stale data after map transitions.
- Align transparency logic with AI systems (specifically the '#' wall fallback).
- Repair outdated verification tests (`tests/verify_phase_20.py`).
- Ensure immediate updates of debug overlay upon map transition.

### Claude's Discretion
- Implementation details of `set_map` and system wiring.
- Specific updates to `tests/verify_phase_20.py` to ensure comprehensive coverage.

### Deferred Ideas (OUT OF SCOPE)
- Adding new debug features (e.g., pathfinding visualization) unless required for fixing existing ones.
- Refactoring the entire ECS architecture.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pygame | 2.5.2+ | Rendering and Input | Project standard |
| Esper | 3.2+ | ECS Framework | Project standard |

## Architecture Patterns

### Recommended Project Structure
No changes to structure, but logic updates to existing files:
- `ecs/systems/debug_render_system.py`: Update logic and signatures.
- `game_states.py`: Update `transition_map` and `draw` calls.
- `tests/verify_phase_20.py`: Update test to match new API.

### Pattern: System State Synchronization
Systems that hold references to the active map must provide a `set_map` method to be called during map transitions. This mirrors the pattern used by `MovementSystem`, `VisibilitySystem`, and `RenderSystem`.

**Example:**
```python
# In DebugRenderSystem
def set_map(self, map_container):
    self.map_container = map_container
```

### Pattern: Unified Transparency Logic
All systems performing visibility checks (Shadowcasting) must use the same transparency criteria.
**Criteria:** A tile is transparent if `tile.transparent == True` AND `tile.sprites.get(SpriteLayer.GROUND) != "#"`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Visibility Logic | Custom raycasting | `VisibilityService.compute_visibility` | Centralized shadowcasting logic |
| Map Layer Access | Direct indexing | `map_container.get_tile(x, y, layer)` | Handles bounds and default layers |

## Common Pitfalls

### Pitfall 1: Stale Map Reference
**What goes wrong:** `DebugRenderSystem` keeps a reference to the initial map. After a `transition_map` call, it continues to query the old map's tiles for visibility and NPC FOV.
**How to avoid:** Call `debug_render_system.set_map(new_map)` in the `transition_map` handler in `game_states.py`.

### Pitfall 2: Layer Mismatch
**What goes wrong:** Debug FOV overlay or NPC FOV is rendered for layer 0 even if the player/NPC is on layer 1 or 2.
**How to avoid:** Pass `player_layer` to the `process` method and use it for filtering and tile lookups.

### Pitfall 3: Transparency Discrepancy
**What goes wrong:** NPC appears to have LOS to the player in debug mode, but the AI doesn't trigger a chase because it considers a `#` sprite as blocking.
**How to avoid:** Explicitly check for the `#` sprite in the `transparency_func` passed to `VisibilityService`.

## Code Examples

### Aligned Transparency Logic
```python
# In ecs/systems/debug_render_system.py
def _render_npc_fov(self, player_layer):
    for ent, (pos, stats, ai) in esper.get_components(Position, Stats, AIBehaviorState):
        if pos.layer != player_layer:
            continue

        def transparency_func(x, y):
            tile = self.map_container.get_tile(x, y, pos.layer)
            if tile:
                # Align with AISystem and VisibilitySystem logic
                if not tile.transparent:
                    return False
                if tile.sprites.get(0) == "#": # 0 is SpriteLayer.GROUND
                    return False
                return True
            return False
        
        # ... compute and render ...
```

### Signature Update in Tests
```python
# In tests/verify_phase_20.py
debug_flags = {"player_fov": True, "npc_fov": True, "chase": True, "labels": True}
player_layer = 0
system.process(surface, debug_flags, player_layer)
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Hardcoded layer 0 | Dynamic `player_layer` | Correct visualization in multi-level maps |
| `tile.transparent` only | `transparent` + `#` check | Accuracy between AI and Debug view |
| Manual sync | `set_map` in transition | Eliminates stale data bugs |

## Open Questions

1. **Should `DebugRenderSystem` be a proper `esper.Processor`?**
   - **What we know:** Currently it is an "explicit-call" system invoked in `Game.draw`.
   - **Recommendation:** Keep it as explicit-call for now to ensure it renders at the correct point in the draw cycle (after map/entities but before UI), but ensure its lifecycle is managed correctly during transitions.

## Sources

### Primary (HIGH confidence)
- `ecs/systems/debug_render_system.py`: Analyzed current implementation.
- `ecs/systems/ai_system.py`: Verified '#' wall fallback logic.
- `ecs/systems/visibility_system.py`: Verified '#' wall fallback logic.
- `game_states.py`: Identified missing synchronization in `transition_map`.
- `tests/verify_phase_20.py`: Identified signature mismatch.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: HIGH

**Research date:** 2024-05-23
**Valid until:** 2024-06-23
