# Phase 13: Range and Movement Rules - Research

**Researched:** 2026-02-14
**Domain:** ECS targeting cursor movement rules — perception-derived range and explored-tile access
**Confidence:** HIGH

## Summary

Phase 13 makes two surgical changes to `move_cursor()` in `ActionSystem`. Currently `move_cursor()` enforces a hardcoded range of 10 (set on the `Targeting` component in Phase 12's Action definition) and only allows movement onto `VisibilityState.VISIBLE` tiles. Phase 13 replaces both behaviors: (1) the range becomes dynamic — derived from the player's `perception` stat at the moment `start_targeting()` is called; (2) the tile-access check expands to allow VISIBLE, SHROUDED, and FORGOTTEN tiles, while still blocking UNEXPLORED tiles.

Both changes are localized. The range fix touches `start_targeting()` where the `Targeting` component is created (to write `stats.perception` into `targeting.range` for inspect mode, overriding the hardcoded `range=10` from the `Action` definition). The tile-access fix touches the visibility check inside `move_cursor()` and the visibility check inside `confirm_action()`. No new components, no new files (besides tests), no new state.

The `Stats` component already has a `perception` field (confirmed: `Stats.perception` is defined in `ecs/components.py` line 32 and set to `10` for the player in `party_service.py` line 14). `VisibilityState` already defines `SHROUDED` and `FORGOTTEN` (confirmed: `map/tile.py` lines 9-11). All the necessary primitives are in place.

**Primary recommendation:** Change two methods in `action_system.py` only: (1) in `start_targeting()`, when `action.targeting_mode == "inspect"`, override `targeting.range` with `stats.perception`; (2) in `move_cursor()`, allow movement when `visibility_state != VisibilityState.UNEXPLORED` instead of requiring `== VisibilityState.VISIBLE`.

---

## Current State Audit (what already exists)

| Item | Location | Current State | Phase 13 Change |
|------|----------|---------------|-----------------|
| `move_cursor()` range check | `action_system.py` line 131 | `if dist > targeting.range: return` — uses `targeting.range` which is 10 from Action definition | No change to this line. Change is upstream: `targeting.range` is set to `stats.perception` in `start_targeting()`. |
| `move_cursor()` visibility check | `action_system.py` lines 135-143 | Only allows `VisibilityState.VISIBLE`; sets `is_visible=True` and moves cursor if visible | Change to allow VISIBLE, SHROUDED, or FORGOTTEN (anything except UNEXPLORED). |
| `confirm_action()` visibility check | `action_system.py` lines 152-162 | Only allows confirming on `VisibilityState.VISIBLE` tiles | Phase 14 defines confirm behavior; this check may need updating too — see Open Questions. |
| `start_targeting()` range assignment | `action_system.py` line 62 | `range=action.range` — uses Action's range field (hardcoded 10 for Investigate) | Add branch: if `action.targeting_mode == "inspect"`, set `range=stats.perception`. |
| `Stats.perception` | `ecs/components.py` line 32 | `perception: int` — defined, value is 10 for player | No change. Already accessible via `stats = esper.component_for_entity(entity, Stats)`. |
| `VisibilityState.SHROUDED` | `map/tile.py` line 11 | `SHROUDED = auto()` | Already imported in `action_system.py` line 5. No import change needed. |
| `VisibilityState.FORGOTTEN` | `map/tile.py` line 12 | `FORGOTTEN = auto()` | Already imported in `action_system.py` line 5. No import change needed. |
| `Action(name="Investigate", range=10, ...)` | `services/party_service.py` line 21 | `range=10` stays as the fallback in the Action definition | No change here. Phase 13 overrides at start_targeting time, not in the Action definition. |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esper` | In use | ECS component queries | All existing systems use it. |
| `math` | Python std | Euclidean distance (`math.sqrt`) | Already imported in `action_system.py` line 2. |
| `map.tile.VisibilityState` | In use | Tile visibility states | Already imported in `action_system.py` line 5. |
| `pytest` | In use | Verification tests | Established pattern in `tests/`. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` | Python std | `Stats`, `Targeting` component definitions | Already used for all components. |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files. All changes are in-place edits to one existing file:

```
ecs/
└── systems/
    └── action_system.py    # CHANGE: start_targeting() + move_cursor()

tests/
└── verify_range_movement.py  # NEW: verification tests
```

### Pattern 1: Dynamic Range From Perception Stat

**What:** In `start_targeting()`, after creating the `Targeting` component, override `targeting.range` with the player's `perception` stat when mode is `"inspect"`.

**Why here, not in the Action definition:** The Action definition in `party_service.py` is static configuration. The perception stat is runtime data. The override belongs in `start_targeting()` which already reads `Stats` (it does so at line 50 for the mana check).

**When to use:** Only for `targeting_mode == "inspect"`. Combat actions use action-defined range (e.g., Ranged has `range=5` which is separate from perception).

```python
# ecs/systems/action_system.py — in start_targeting(), after Targeting is constructed:
# FROM (lines 57-65):
targeting = Targeting(
    origin_x=pos.x, origin_y=pos.y,
    target_x=pos.x, target_y=pos.y,
    range=action.range,
    mode=action.targeting_mode,
    action=action
)
if action.targeting_mode == "auto":
    ...

# TO: add perception override for inspect mode BEFORE adding component:
targeting = Targeting(
    origin_x=pos.x, origin_y=pos.y,
    target_x=pos.x, target_y=pos.y,
    range=action.range,
    mode=action.targeting_mode,
    action=action
)
if action.targeting_mode == "inspect":
    targeting.range = stats.perception   # Dynamic range from player stat (INV-02)
if action.targeting_mode == "auto":
    ...
```

**Note:** `stats` is already bound at line 50 of `start_targeting()` for the mana check. No extra ECS query needed.

### Pattern 2: Allow Explored Tiles in move_cursor

**What:** Change the visibility check in `move_cursor()` from "must be VISIBLE" to "must not be UNEXPLORED."

**When to use:** This change is unconditional — all modes benefit from correct tile access. For combat `"auto"` targeting this check is irrelevant (cursor jumps to enemies, not free-moved), but the logic change is safe regardless of mode.

```python
# ecs/systems/action_system.py — in move_cursor(), lines 134-143:
# FROM:
is_visible = False
for layer in self.map_container.layers:
    if 0 <= new_y < len(layer.tiles) and 0 <= new_x < len(layer.tiles[new_y]):
        if layer.tiles[new_y][new_x].visibility_state == VisibilityState.VISIBLE:
            is_visible = True
            break

if is_visible:
    targeting.target_x = new_x
    targeting.target_y = new_y

# TO:
is_accessible = False
for layer in self.map_container.layers:
    if 0 <= new_y < len(layer.tiles) and 0 <= new_x < len(layer.tiles[new_y]):
        if layer.tiles[new_y][new_x].visibility_state != VisibilityState.UNEXPLORED:
            is_accessible = True
            break

if is_accessible:
    targeting.target_x = new_x
    targeting.target_y = new_y
```

**Why "not UNEXPLORED" instead of listing allowed states:** The goal says "explored (shrouded/forgotten) tiles." The VisibilityState enum has exactly four values: UNEXPLORED, VISIBLE, SHROUDED, FORGOTTEN. Three of the four are allowed. Checking `!= UNEXPLORED` is simpler, less fragile to future new states, and directly encodes the rule "player has seen this tile."

**Alternative (explicit allowlist):**
```python
if layer.tiles[new_y][new_x].visibility_state in (
    VisibilityState.VISIBLE,
    VisibilityState.SHROUDED,
    VisibilityState.FORGOTTEN
):
```
This is more explicit but requires updating if a new allowed state is ever added. Either approach is correct; the `!= UNEXPLORED` form is more concise and directly matches the spec language.

### Anti-Patterns to Avoid

- **Changing `Action(name="Investigate", range=10, ...)` in `party_service.py`:** The Action's `range=10` is a reasonable fallback. Phase 13 overrides it dynamically. Removing the hardcoded range from the Action would break the fallback for any code that reads `action.range` before `start_targeting()` runs.
- **Overriding range AFTER `esper.add_component()`:** The Targeting component must have its correct range before any cursor movement is processed. Set `targeting.range` before calling `esper.add_component(entity, targeting)`.
- **Checking `action.targeting_mode` on the Action, not on `targeting.mode`:** Inside `start_targeting()` either field works. The `action` local variable is in scope. Use `action.targeting_mode` for consistency with the pattern already used at line 67.
- **Modifying `find_potential_targets()` or `cycle_targets()`:** Phase 13 does not change these. They are combat-mode functions and remain unchanged.
- **Changing `confirm_action()` visibility check for Phase 13:** Phase 14 defines what confirming on a SHROUDED tile should do (show tile name only, no entity info). For Phase 13, the `confirm_action()` visibility check is intentionally unchanged — confirming during inspect mode is currently a no-op (from Phase 12), and Phase 14 will add the actual output logic at that time. See Open Questions section.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Perception-based range | Custom range formula or new config field | `stats.perception` directly | `Stats.perception` is already the authoritative perception value. Single source of truth. |
| "Has player seen tile" check | Custom visited-tile tracker | `tile.visibility_state != VisibilityState.UNEXPLORED` | `VisibilityState` already encodes exactly this. UNEXPLORED is the only "never seen" state. |
| Per-mode cursor rules | Separate move_cursor functions or cursor subclasses | Mode check inside existing `move_cursor()` | `move_cursor()` already receives the entity and reads `Targeting` which has `mode`. A single function handles all modes cleanly. |

**Key insight:** All the data Phase 13 needs (perception stat, tile visibility state) is already in the ECS world and already accessible in the relevant functions. The changes are read-path changes only — no new writes, no new components, no new events.

---

## Common Pitfalls

### Pitfall 1: Stats query location in start_targeting

**What goes wrong:** The mana check at line 50-52 already calls `stats = esper.component_for_entity(entity, Stats)`. If the range-override code is placed AFTER the `if action.targeting_mode == "auto":` block (which is after the `esper.add_component` call at line 81), the override happens too late — the component is already attached with the wrong range value.

**Why it happens:** The flow in `start_targeting()` is: (1) get stats, (2) create Targeting, (3) handle auto mode (find targets), (4) add component, (5) set state. The override must happen between steps 2 and 4.

**How to avoid:** Place the `if action.targeting_mode == "inspect": targeting.range = stats.perception` block immediately after the `Targeting(...)` construction call and before the `if action.targeting_mode == "auto":` block.

**Warning signs:** Cursor can move only within combat-action range (5 tiles for Ranged action) or cursor range does not change when perception stat changes.

### Pitfall 2: Cursor can move to VISIBLE-only tiles initially

**What goes wrong:** Only changing `start_targeting()` without changing `move_cursor()` means the cursor appears but still cannot move to SHROUDED tiles. Success criteria 2 would fail.

**Why it happens:** `move_cursor()` has its own independent visibility check at lines 135-142. Changing the range in `start_targeting()` does not affect the tile-access check.

**How to avoid:** Apply both changes: range in `start_targeting()` AND tile-access in `move_cursor()`. They are independent and both required.

**Warning signs:** Cursor moves freely within VISIBLE tiles but stops at the VISIBLE/SHROUDED boundary even when within perception range.

### Pitfall 3: confirm_action() still requires VISIBLE tile

**What goes wrong:** After Phase 13, the cursor can sit on a SHROUDED tile. If the player presses Enter (confirm), `confirm_action()` checks `VisibilityState.VISIBLE` and returns `False`, silently doing nothing. This is actually acceptable for Phase 13 (Phase 14 will add the actual output logic and update `confirm_action()` accordingly). However, it can be confusing during testing if Enter appears to do nothing on SHROUDED tiles.

**Why it happens:** `confirm_action()` has its own visibility check at lines 152-162, still requiring VISIBLE. Phase 13 intentionally leaves this unchanged.

**How to avoid:** Document in tests that confirming on a SHROUDED tile returns False in Phase 13. Phase 14 will change `confirm_action()` to handle SHROUDED tiles.

**Warning signs:** None — this is expected behavior for Phase 13. Test that confirm returns False on SHROUDED tiles (to lock in the known state for Phase 14 to change).

### Pitfall 4: Multi-layer map range check

**What goes wrong:** The visibility check in `move_cursor()` iterates over all layers. If any layer has the tile as non-UNEXPLORED, movement is allowed. This is the correct behavior (same as the existing pattern). If this iteration were changed to "all layers must be non-UNEXPLORED" it would break multi-layer maps.

**Why it happens:** The existing pattern uses the first layer with a non-UNEXPLORED tile. This is already the correct semantic.

**How to avoid:** Keep the `break` after setting `is_accessible = True`. Do not change the iteration logic.

### Pitfall 5: Euclidean distance vs Chebyshev/Manhattan for range

**What goes wrong:** The range check uses `math.sqrt((new_x - origin_x)**2 + (new_y - origin_y)**2)`, which is Euclidean distance. With `perception=10`, the cursor can reach tiles in a circle of radius 10 — roughly 28x28 tiles worth of area. Moving diagonally, each step costs `math.sqrt(2) ≈ 1.41` range, so the cursor can make 7 diagonal moves before hitting the range limit, vs 10 cardinal moves.

**Why it matters:** This is already the behavior from Phase 12 (move_cursor was already written this way). Phase 13 simply makes the range value come from perception instead of being hardcoded 10. No change is needed to the distance formula itself.

**How to avoid:** No action required. Document that Euclidean distance is the established convention for range in this codebase (also used in `find_potential_targets()` at line 92).

---

## Code Examples

Verified patterns from the existing codebase:

### Current start_targeting — range comes from action.range (to be extended)
```python
# action_system.py lines 48-83 — current, Phase 13 adds perception override
def start_targeting(self, entity, action):
    stats = esper.component_for_entity(entity, Stats)          # line 50
    if action.cost_mana > stats.mana:
        return False

    pos = esper.component_for_entity(entity, Position)

    targeting = Targeting(
        origin_x=pos.x, origin_y=pos.y,
        target_x=pos.x, target_y=pos.y,
        range=action.range,          # <-- Phase 13 overrides this for inspect mode
        mode=action.targeting_mode,
        action=action
    )
    # Phase 13 adds here:
    # if action.targeting_mode == "inspect":
    #     targeting.range = stats.perception

    if action.targeting_mode == "auto":
        ...

    esper.add_component(entity, targeting)
    self.turn_system.current_state = GameStates.TARGETING
    return True
```

### Current move_cursor — visibility check (to be changed)
```python
# action_system.py lines 123-146 — current
def move_cursor(self, entity, dx, dy):
    try:
        targeting = esper.component_for_entity(entity, Targeting)
        new_x = targeting.target_x + dx
        new_y = targeting.target_y + dy

        # Range check — no change in Phase 13 (uses targeting.range which is now dynamic)
        dist = math.sqrt((new_x - targeting.origin_x)**2 + (new_y - targeting.origin_y)**2)
        if dist > targeting.range:
            return

        # Visibility check — Phase 13 changes this:
        # FROM: only VISIBLE tiles allowed
        is_visible = False
        for layer in self.map_container.layers:
            if 0 <= new_y < len(layer.tiles) and 0 <= new_x < len(layer.tiles[new_y]):
                if layer.tiles[new_y][new_x].visibility_state == VisibilityState.VISIBLE:
                    is_visible = True
                    break

        if is_visible:
            targeting.target_x = new_x
            targeting.target_y = new_y
    except KeyError:
        pass
```

### After Phase 13 changes:
```python
# start_targeting() — perception override for inspect mode
if action.targeting_mode == "inspect":
    targeting.range = stats.perception

# move_cursor() — expanded tile access
is_accessible = False
for layer in self.map_container.layers:
    if 0 <= new_y < len(layer.tiles) and 0 <= new_x < len(layer.tiles[new_y]):
        if layer.tiles[new_y][new_x].visibility_state != VisibilityState.UNEXPLORED:
            is_accessible = True
            break

if is_accessible:
    targeting.target_x = new_x
    targeting.target_y = new_y
```

### Player Stats with perception field (confirmed existing)
```python
# services/party_service.py line 14
Stats(hp=100, max_hp=100, power=5, defense=2, mana=50, max_mana=50, perception=10, intelligence=10)
# Stats.perception is int, already in place. Phase 13 reads it in start_targeting().
```

### VisibilityState enum (confirmed existing)
```python
# map/tile.py lines 7-12
class VisibilityState(Enum):
    UNEXPLORED = auto()   # Never seen — cursor CANNOT move here
    VISIBLE    = auto()   # Currently visible — cursor CAN move here
    SHROUDED   = auto()   # Previously seen, not currently lit — cursor CAN move here
    FORGOTTEN  = auto()   # Memory faded — cursor CAN move here
```

---

## State of the Art

| Old Behavior | Phase 13 Behavior | What Changes |
|--------------|-------------------|--------------|
| Investigate cursor range = 10 (hardcoded in Action) | Range = player's perception stat (10 by default, but dynamic) | `start_targeting()` overrides `targeting.range` with `stats.perception` for inspect mode |
| Cursor can only move to VISIBLE tiles | Cursor can move to VISIBLE, SHROUDED, or FORGOTTEN tiles | `move_cursor()` checks `!= UNEXPLORED` instead of `== VISIBLE` |
| Phase 12 cursor visible-only | Full investigation range including explored-but-dark tiles | Two targeted changes to `action_system.py` |

---

## Open Questions

1. **Should `confirm_action()` allow confirming on SHROUDED/FORGOTTEN tiles in Phase 13?**
   - What we know: Phase 14 adds inspection output for SHROUDED tiles (SC-2: "Confirming on a SHROUDED tile prints only the tile name"). Phase 13 success criteria do not mention confirm behavior.
   - What's unclear: Should Phase 13 change `confirm_action()` to accept non-VISIBLE tiles, or leave that for Phase 14?
   - Recommendation: Leave `confirm_action()` unchanged in Phase 13. The current behavior (returns False silently on non-VISIBLE) is acceptable because Phase 12 made confirm a no-op anyway. Phase 14 will update `confirm_action()` to produce output and will naturally remove the VISIBLE-only restriction. Changing it in Phase 13 would be premature.

2. **Should FORGOTTEN tiles be included in accessible tiles?**
   - What we know: The goal says "explored (shrouded/forgotten) tiles." Success criterion 2 says "SHROUDED (previously seen) tiles." FORGOTTEN is also previously seen (it is a decayed memory of SHROUDED).
   - What's unclear: Does "SHROUDED" in the spec text mean only SHROUDED, or does it mean "any previously-seen tile including FORGOTTEN"?
   - Recommendation: Include FORGOTTEN. The goal text explicitly says "shrouded/forgotten." The intent is "any tile the player has seen before" = anything except UNEXPLORED. The `!= UNEXPLORED` formulation covers this cleanly without ambiguity.

3. **Does the `range=10` in the Action definition need to change?**
   - What we know: Phase 13 overrides `targeting.range` in `start_targeting()`. The `Action.range=10` value is only read in `start_targeting()` to initialize `targeting.range`, which is then immediately overridden for inspect mode.
   - Recommendation: Leave `Action.range=10` unchanged. It serves as a readable default and as a fallback if inspect mode is ever invoked via a code path that bypasses `start_targeting()`. Removing it would gain nothing.

---

## Sources

### Primary (HIGH confidence)
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/action_system.py` — Confirmed: `start_targeting()` at lines 48-83; `move_cursor()` at lines 123-146; `confirm_action()` at lines 148-182; `stats` already bound in `start_targeting()` at line 50; VisibilityState.VISIBLE check at lines 136-141.
- `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — Confirmed: `Stats.perception: int` at line 32; `Targeting.range: int` at line 88; both are standard int fields.
- `/home/peter/Projekte/rogue_like_rpg/map/tile.py` — Confirmed: `VisibilityState` enum with UNEXPLORED, VISIBLE, SHROUDED, FORGOTTEN at lines 7-12.
- `/home/peter/Projekte/rogue_like_rpg/services/party_service.py` — Confirmed: Player created with `perception=10` at line 14; Investigate action with `range=10, targeting_mode="inspect"` at line 21.
- `python -m pytest tests/verify_action_wiring.py -v` — All 7 Phase 12 tests pass; Phase 12 complete baseline confirmed.

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` — Phase 13 goal "movement is allowed over explored (shrouded/forgotten) tiles" and success criteria INV-02, TILE-03 confirmed.
- `.planning/phases/12-action-wiring/12-RESEARCH.md` — Prior decisions confirmed; architecture constraints locked.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; two localized edits to one existing Python file.
- Architecture: HIGH — both change locations are precisely identified from direct code audit; no ambiguity about where changes go.
- Pitfalls: HIGH — all identified from direct inspection of `action_system.py`; the multi-step "stats is already bound" insight is verified from the actual code.
- FORGOTTEN tile inclusion: MEDIUM — inferred from goal text vs SC-2 wording; confirmed as correct by the `!= UNEXPLORED` formulation matching project intent.

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable codebase; no external dependencies)
