---
task: fix-map-container-attribute-error
files_modified: [map/map_container.py]
---

# Fix MapContainer Attribute Error

**Goal:** Implement `is_walkable(x, y)` in `MapContainer` to resolve the `AttributeError` in `DeathSystem`.

## Problem
`DeathSystem` calls `self.map_container.is_walkable(x, y)`, but `MapContainer` does not have this method.

## Solution
Add `is_walkable(x, y)` to `MapContainer`. It should:
1. Check if (x, y) is within map bounds.
2. Get the tile at (x, y) on layer 0 (ground layer).
3. Return `tile.walkable` if the tile exists, else `False`.

## Tasks
1. Implement `is_walkable` in `map/map_container.py`.
2. Verify with `tests/verify_loot_system.py`.
