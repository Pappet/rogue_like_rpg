
## 2024-05-24 - Optimization: Caching transparency function per layer for FOV compute
**Learning:** The visibility system computes FOV repeatedly using a nested function to fetch tiles and check their transparency. Profiling shows that function setup and grid index validation during raycasting is a hot path (approx 30% of FOV compute time). Python index out-of-bounds error handling is slightly faster than pre-validating coords.
**Action:** Used a dictionary in `VisibilitySystem` to cache the transparency function per `layer_index` per frame, and switched to using a `try...except IndexError` structure for bounding checks inside `is_transparent`. Applied the same optimization to `AISystem` which also calculates line-of-sight. The result is a ~20% speedup in transparency checks.

## 2024-06-20 - Optimization: Pre-calculating length bounds for transparency check closure
**Learning:** In hot path loop closures like `is_transparent` which is passed to the visibility FOV service, pre-calculating list bounds using `len(x)` outside of the inner loop is significantly faster than relying on a `try...except IndexError` structure for out of bounds access, avoiding costly exception overhead.
**Action:** When working on tight loop closures, cache required references (like `layer_tiles`) and their dimensions (`len_y`) prior to defining the closure. This avoids repeated evaluation without compromising boundary checks.
