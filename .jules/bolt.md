
## 2024-05-24 - Optimization: Caching transparency function per layer for FOV compute
**Learning:** The visibility system computes FOV repeatedly using a nested function to fetch tiles and check their transparency. Profiling shows that function setup and grid index validation during raycasting is a hot path (approx 30% of FOV compute time). Python index out-of-bounds error handling is slightly faster than pre-validating coords.
**Action:** Used a dictionary in `VisibilitySystem` to cache the transparency function per `layer_index` per frame, and switched to using a `try...except IndexError` structure for bounding checks inside `is_transparent`. Applied the same optimization to `AISystem` which also calculates line-of-sight. The result is a ~20% speedup in transparency checks.
