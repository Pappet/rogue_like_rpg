
## 2024-05-24 - Optimization: Caching transparency function per layer for FOV compute
**Learning:** The visibility system computes FOV repeatedly using a nested function to fetch tiles and check their transparency. Profiling shows that function setup and grid index validation during raycasting is a hot path (approx 30% of FOV compute time). Python index out-of-bounds error handling is slightly faster than pre-validating coords.
**Action:** Used a dictionary in `VisibilitySystem` to cache the transparency function per `layer_index` per frame, and switched to using a `try...except IndexError` structure for bounding checks inside `is_transparent`. Applied the same optimization to `AISystem` which also calculates line-of-sight. The result is a ~20% speedup in transparency checks.

## 2024-05-25 - Optimization: Reverted to pre-calculated bounds check instead of try-except for FOV
**Learning:** While earlier I found `try...except IndexError` was slightly faster than re-validating coords in FOV raycasting, a new test comparing `try...except` against *pre-calculating* grid bounds and direct indexing proved that pre-calculated bounds checking is actually significantly faster (about 2x faster). The `try...except` overhead in Python is high.
**Action:** Replaced `try...except IndexError` and redundant dynamic `len()` evaluations in the `get_is_transparent` and `_make_transparency_func` closures with pre-calculated `height` and `width` bounds checks. This avoids the high exception overhead and repetitive length calculations in the hot path.
