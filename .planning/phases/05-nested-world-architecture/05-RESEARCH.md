# Phase 5: Nested World Architecture - Research

**Researched:** 2024-05-22
**Domain:** ECS World Management & Navigation
**Confidence:** HIGH

## Summary

This phase implements the capability to navigate between distinct map environments (e.g., transitioning from a global "World" map to a local "House" map). The core requirements are a `Portal` component to define transition points and a `MapService` upgrade to manage multiple persistent `MapContainer` instances.

The recommended approach uses a **Repository Pattern** within `MapService` to hold active and inactive maps. Transitions are handled via an **Event-Driven** flow where the `ActionSystem` detects a portal interaction and dispatches a request, which the main `Game` state fulfills by swapping the active map and migrating the player.

**Primary recommendation:** Upgrade `MapService` to store a dictionary of `MapContainer` objects and implement an `Entity Persistence` strategy to freeze/thaw entities on inactive maps.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `MapService` | Internal | Map Manager | Centralizes map lifecycle and storage. |
| `esper` | Existing | Event Dispatch | Decouples "Actions" from "State Transitions". |
| `Portal` | Component | Navigation | Standard data-driven way to link game spaces. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pickle` | Std Lib | Serialization | For deep-copying entity state (if needed). |
| `copy` | Std Lib | Persistence | `deepcopy` for preserving map state. |

**Installation:**
N/A (Internal architectural changes).

## Architecture Patterns

### Repository Pattern (MapService)
The `MapService` becomes the source of truth for all world data, not just a generator.

```python
class MapService:
    def __init__(self):
        self._maps: Dict[str, MapContainer] = {}
        self.active_map_id: str = None
    
    def register_map(self, map_id: str, container: MapContainer):
        self._maps[map_id] = container
        
    def get_map(self, map_id: str) -> MapContainer:
        return self._maps.get(map_id)
```

### Event-Driven Transitions
Decouple the *detection* of a transition from the *execution* of it.

1.  **ActionSystem:** Detects `EnterPortal` action -> Dispatches `change_map` event.
2.  **Game State:** Listens for `change_map` -> Calls `MapService.set_active_map` -> Updates ECS.

### Entity Persistence (Freeze/Thaw)
When switching maps, entities (except Player) must be preserved.

*   **Freeze:** On exit, serialize all non-player entities into `MapContainer.frozen_entities`. Remove from `esper`.
*   **Thaw:** On enter, deserialize `MapContainer.frozen_entities` back into `esper`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Map Storage | Custom File I/O (yet) | In-Memory `Dict` | Simpler for now; allows `pickle` later. |
| Entity IDs | Custom ID Manager | `esper.create_entity` | Let ECS handle ID generation; IDs are transient. |
| Event Bus | Custom Observer | `esper.dispatch_event` | Already integrated and sufficient. |

**Key insight:** Don't complicate persistence with database/file formats yet. Python's object model is sufficient for session-based persistence.

## Common Pitfalls

### Pitfall 1: Entity ID Invalidation
**What goes wrong:** Entities targeting other entities (e.g., `AttackIntent(target=123)`) break when switching maps because IDs change on reload.
**Why it happens:** `esper` generates new integer IDs when entities are re-created.
**How to avoid:** Clear all transient components (`AttackIntent`, `Targeting`) upon map transition.
**Warning signs:** Crashes accessing non-existent entities after using a portal.

### Pitfall 2: Player Positioning Race Condition
**What goes wrong:** Player moves to new map but keeps old coordinates, ending up in a wall.
**Why it happens:** Updating `active_map` without immediately updating `Player.Position`.
**How to avoid:** The transition logic must atomic: `Load Map` -> `Update Player Pos` -> `Render`.

### Pitfall 3: Global System Desync
**What goes wrong:** Systems like `VisibilitySystem` continue using the old map reference.
**Why it happens:** Systems are initialized with `map_container` in `__init__`.
**How to avoid:** Systems should reference `MapService` (singleton/service) to always get `current_map`, OR `Game` state must re-inject the new map into systems.

## Code Examples

### Portal Component
```python
# Source: Internal Best Practice
@dataclass
class Portal:
    target_map_id: str
    target_x: int
    target_y: int
    target_layer: int = 0
    # Optional: logic for "locked" portals
    requires_key: str = None 
```

### Transition Logic (Game State)
```python
# Source: Architecture Pattern
def transition_map(self, target_map_id, target_x, target_y):
    # 1. Freeze current entities
    self.map_service.freeze_entities(self.world, exclude=[self.player_entity])
    
    # 2. Switch Map
    new_map = self.map_service.get_map(target_map_id)
    self.map_container = new_map
    
    # 3. Update Player
    player_pos = self.world.component_for_entity(self.player_entity, Position)
    player_pos.x = target_x
    player_pos.y = target_y
    
    # 4. Thaw new entities
    self.map_service.thaw_entities(self.world, new_map)
    
    # 5. Update Systems
    self.visibility_system.set_map(new_map)
    self.movement_system.set_map(new_map)
    # ... other systems
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single Map | Multi-Container | Phase 5 | Allows "World" vs "Interior" logic. |
| Global State | Repository | Phase 5 | encapsulated state management. |

**Deprecated/outdated:**
- **Direct Map Swapping:** `current_map = new_map` without persistence causes data loss.

## Open Questions

1.  **Inventory Persistence**
    - What we know: `Inventory` is a component on Player.
    - What's unclear: Are items on the ground Entities?
    - Recommendation: Treat ground items as Entities (freeze/thaw). Inventory items are data (persist with Player).

2.  **Time Propagation**
    - What we know: Turn system advances time.
    - What's unclear: Do inactive maps "simulate" time?
    - Recommendation: For Phase 5, freeze time on inactive maps. "Aging" is Phase 6.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Standard ECS patterns.
- Architecture: HIGH - Repository pattern is well-understood.
- Pitfalls: MEDIUM - Specific implementation details of `esper` might reveal edge cases.

**Research date:** 2024-05-22
**Valid until:** Phase 6 (Advanced Navigation)
