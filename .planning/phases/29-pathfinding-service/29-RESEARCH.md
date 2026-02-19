# Phase 29: Pathfinding Service - Research

**Researched:** 2025-05-15
**Domain:** Pathfinding, Navigation, AI
**Confidence:** HIGH

## Summary

Phase 29 introduces a robust pathfinding infrastructure to replace/augment the current "greedy Manhattan" and "random wander" AI behaviors. The core of this phase is the `PathfindingService`, which uses the A* algorithm to find optimal walkable paths between points on a map, accounting for both static terrain (walls) and dynamic entities (blockers).

The primary recommendation is to integrate the `pathfinding` library (pure Python) to avoid hand-rolling complex A* logic and to ensure reliability and performance on standard roguelike map sizes (40x40 to 100x100). NPCs will now use a `PathData` component to store these precomputed paths, consuming them step-by-step during their turns. This foundation is critical for the upcoming NPC Schedules (Phase 31) where characters must navigate purposefully to specific locations.

**Primary recommendation:** Use the `pathfinding` library for A* calculation and implement a `PathfindingService` that builds a weight matrix from `MapContainer` and `esper` entity blockers.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pathfinding` | ^1.0.9 | A* Algorithm | Pure Python, lightweight, supports grid-based navigation, handles custom weights and diagonal movement controls. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `heapq` | (stdlib) | Priority Queue | Used internally by most A* implementations (including `pathfinding`) for efficient node selection. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `pathfinding` | `tcod.path` | `tcod` is much faster (C-level) but is a heavy binary dependency; `pathfinding` is pure Python and easier to integrate into the existing "lightweight" stack. |
| `pathfinding` | Hand-rolled A* | Risk of bugs in edge cases (re-opening nodes, diagonals); violates "Don't Hand-Roll" constraint. |

**Installation:**
```bash
pip install pathfinding
```

## Architecture Patterns

### Recommended Project Structure
```
services/
└── pathfinding_service.py  # A* wrapper integrating MapContainer + Blockers
ecs/
├── components.py           # Add PathData component
└── systems/
    └── ai_system.py        # Update to handle PathData consumption
```

### Pattern 1: Grid Matrix Construction
To integrate with `esper` blockers efficiently, the service should build a fresh matrix (or update a cached one) once per pathfinding request.
**Pattern:**
1. Initialize a 2D matrix (Width x Height) from `MapContainer` walkability.
2. Iterate all entities with `(Position, Blocker)` and set matrix cells to 0 (blocked).
3. Special case: Set the `destination` tile to 1 (walkable) even if blocked by an entity (to allow pathing *to* a target like the player).

### Pattern 2: Path Consumption
The `PathData` component should be treated as a stack or queue.
**What:** `PathData` stores `path: List[Tuple[int, int]]`.
**When to use:** In `AISystem`, if an entity has `PathData` and it's not empty, pop the first element and move.
**Validation:** If the next tile is blocked by another entity, the path is "invalidated" and must be recomputed or the entity waits.

### Anti-Patterns to Avoid
- **Global Path Refresh:** Recomputing paths for all NPCs every turn is O(N_NPCs * A*). Only recompute when the destination changes or the path is physically blocked.
- **Ignoring claimed_tiles:** NPCs should still use the `claimed_tiles` set during `AISystem.process` to prevent multiple entities from stepping onto the same tile in the same turn, even with pathfinding.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| A* Algorithm | Custom A* loop | `pathfinding.finder.a_star.AStarFinder` | Proven logic; handles edge cases and is optimized. |
| Graph Nodes | Custom Node objects | `pathfinding.core.grid.Grid` | Integrated with the finder; supports weights and diagonal rules. |
| Priority Queue | Custom sorting | `heapq` (or library internal) | Essential for A* performance. |

**Key insight:** Hand-rolling A* often leads to subtle bugs like "cutting corners" on diagonal walls or inefficient node re-expansion. Using a library ensures the core algorithm is solid.

## Common Pitfalls

### Pitfall 1: Destination is Blocked
**What goes wrong:** If the goal tile (e.g., the player) has a `Blocker` component, A* will return "No Path".
**Why it happens:** The algorithm sees the target node as unwalkable.
**How to avoid:** Temporarily mark the destination tile as walkable in the `Grid` matrix before calling `find_path`, or path to an adjacent tile.

### Pitfall 2: Diagonal Wall Clipping
**What goes wrong:** NPCs might try to squeeze diagonally between two walls (e.g., (0,0) and (1,1) are walls, NPC tries to go from (1,0) to (0,1)).
**How to avoid:** Use `DiagonalMovement.never` in `AStarFinder` for cardinal-only movement, or `DiagonalMovement.only_when_no_obstacle` for 8-way movement.

### Pitfall 3: Stale Paths
**What goes wrong:** NPC follows a path toward a destination that has since moved (e.g., a fleeing player or a moving shopkeeper).
**How to avoid:** Store the `destination` coordinates in `PathData`. If the target entity's position != `PathData.destination`, trigger a recompute.

## Code Examples

Verified patterns using the `pathfinding` library:

### Pathfinding Service Wrapper
```python
# Source: https://github.com/brean/python-pathfinding
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

class PathfindingService:
    @staticmethod
    def get_path(world, map_container, start, end, layer=0):
        # 1. Build matrix from MapContainer (1=walkable, 0=blocked)
        width, height = map_container.width, map_container.height
        matrix = [[1 if map_container.is_walkable(x, y) else 0 
                  for x in range(width)] for y in range(height)]
        
        # 2. Add entity blockers from ECS
        for ent, (pos, _) in world.get_components(Position, Blocker):
            if pos.layer == layer:
                # Don't block the end point if we want to path TO it
                if (pos.x, pos.y) != end:
                    matrix[pos.y][pos.x] = 0
        
        # 3. Compute A*
        grid = Grid(matrix=matrix)
        start_node = grid.node(start[0], start[1])
        end_node = grid.node(end[0], end[1])
        
        # Cardinal movement only (standard for this project)
        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        path, runs = finder.find_path(start_node, end_node, grid)
        
        # Return list of (x, y), skipping the current position
        return [(n.x, n.y) for n in path[1:]]
```

### Component Definition
```python
@dataclass
class PathData:
    path: List[Tuple[int, int]] = field(default_factory=list)
    destination: Tuple[int, int] = (0, 0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Greedy Manhattan | A* Pathfinding | Phase 29 | NPCs navigate around corners and through corridors reliably. |
| Random Wander | Purposeful Navigation | Phase 29 | Enables NPC Schedules (WORK/HOME/SOCIALIZE). |

## Open Questions

1. **Wait or Recompute?**
   - What we know: If the next step is blocked by another NPC, we must recompute or wait.
   - What's unclear: Should NPCs "wait" for 1 turn before recomputing to see if the block clears (e.g., another NPC moving)?
   - Recommendation: Recompute immediately if the path is blocked to find an alternative route, but implement a "patience" counter if performance becomes an issue.

2. **Diagonal Support**
   - What we know: `AISystem` currently uses cardinal directions.
   - What's unclear: Should we enable 8-way movement for pathfinding?
   - Recommendation: Stick to cardinal for Phase 29 to maintain consistency with existing `movement_system` logic.

## Sources

### Primary (HIGH confidence)
- Official `pathfinding` GitHub Repo: [https://github.com/brean/python-pathfinding](https://github.com/brean/python-pathfinding)
- Codebase check: `ecs/systems/movement_system.py` (Blocker logic)
- Codebase check: `map/map_container.py` (Walkability logic)

### Secondary (MEDIUM confidence)
- "A* Pathfinding for Roguelikes" patterns from Common Roguelike Tutorials.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `pathfinding` is the go-to pure Python library.
- Architecture: HIGH - Fits the existing Service/ECS pattern perfectly.
- Pitfalls: HIGH - Covers all standard navigation bugs.

**Research date:** 2025-05-15
**Valid until:** 2025-06-15
