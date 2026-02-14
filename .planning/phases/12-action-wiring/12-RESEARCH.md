# Phase 12: Action Wiring - Research

**Researched:** 2026-02-14
**Domain:** ECS targeting system extension — inspect mode cursor, header text, cursor color
**Confidence:** HIGH

## Summary

Phase 12 wires the existing "Investigate" action in the player's `ActionList` through the existing targeting system. The `Targeting` component, `GameStates.TARGETING` state, `draw_targeting_ui()`, and cursor/arrow-key handling are already fully implemented and working for combat targeting. Phase 12 reuses all of this with minimal surgical changes.

The core changes are: (1) add `requires_targeting=True`, `targeting_mode="inspect"`, and a usable `range` to the Investigate `Action` in `PartyService`; (2) make `draw_targeting_ui()` in `RenderSystem` use cyan for inspect mode and yellow for combat mode; (3) make `draw_header()` in `UISystem` read the active `Targeting` component's mode to distinguish "Investigating..." from "Targeting..."; (4) prevent `confirm_action()` from calling `end_player_turn()` when mode is "inspect" (investigation is a free action — INV-03); (5) guard `Description.get()` calls against entities without a `Stats` component (the spec note says `stats=None` must not crash — needed for Phase 14 but the guard must be placed in Phase 12 or earlier).

No new components, no new game states, no new systems, no new files (except tests). All changes are small in-place modifications to four existing files.

**Primary recommendation:** Wire Investigate by changing five specific locations: `party_service.py` (Action definition), `action_system.py` (skip `end_player_turn` for inspect mode), `render_system.py` (cursor color by mode), `ui_system.py` (header text by mode), and `ecs/components.py` (`Description.get` accepts `stats=None`).

---

## Current State Audit (what already exists)

| Item | Location | State |
|------|----------|-------|
| `Action(name="Investigate")` | `services/party_service.py` line 21 | EXISTS — but `requires_targeting=False`, `range=0`, `targeting_mode="auto"`. Needs update. |
| `GameStates.TARGETING` | `config.py` line 64 | EXISTS — used for all targeting. No new state needed. |
| `Targeting` component with `.mode` field | `ecs/components.py` line 83 | EXISTS — `mode: str` field already present, set from `action.targeting_mode`. |
| `draw_targeting_ui()` | `ecs/systems/render_system.py` lines 84-121 | EXISTS — hardcodes yellow (255,255,0) for BOTH range highlight and cursor box. Needs color parameterization. |
| Arrow-key cursor movement in TARGETING state | `game_states.py` lines 206-228 | EXISTS — `move_cursor()` called on arrow keys. No change needed. |
| Escape cancel in TARGETING state | `game_states.py` line 209 | EXISTS — calls `cancel_targeting()`. No change needed. |
| `cancel_targeting()` restores PLAYER_TURN | `ecs/systems/action_system.py` lines 182-185 | EXISTS — removes Targeting component, sets `PLAYER_TURN`. No turn consumed. Correct for free action. |
| `confirm_action()` calls `end_player_turn()` | `ecs/systems/action_system.py` line 177 | EXISTS — always calls `end_player_turn()`. For inspect mode, must NOT call it (INV-03). |
| Header "Targeting..." text | `ecs/systems/ui_system.py` lines 44-46 | EXISTS — shows "Targeting..." for ALL `GameStates.TARGETING`. Must distinguish inspect vs combat mode. |
| `Description.get(stats)` method | `ecs/components.py` lines 104-108 | EXISTS — but crashes if `stats=None`. Must accept `None` gracefully. |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `esper` | In use | ECS component queries, event dispatch | All existing systems use it. |
| `pygame` | In use | Color constants, drawing | Already used in `RenderSystem` and `UISystem`. |
| `dataclasses` | Python Std | `Action`, `Targeting` component definitions | Already used for all components. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | In use | Verification tests | Established pattern in `tests/`. |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

No new files. All changes are in-place edits to existing files:

```
services/
└── party_service.py      # CHANGE: Investigate Action definition

ecs/
├── components.py         # CHANGE: Description.get(stats=None) guard
└── systems/
    ├── action_system.py  # CHANGE: skip end_player_turn for inspect mode
    ├── render_system.py  # CHANGE: cursor color by targeting mode
    └── ui_system.py      # CHANGE: header text by targeting mode

tests/
└── verify_action_wiring.py   # NEW: verification tests
```

### Pattern 1: Parameterize Action for Targeting Mode

**What:** Update the "Investigate" `Action` in `PartyService` to flag it as a targeting action with the `"inspect"` mode and a reasonable range.
**When to use:** This is the single source of truth for action configuration.

```python
# services/party_service.py — change line 21
# FROM:
Action(name="Investigate"),
# TO:
Action(name="Investigate", range=10, requires_targeting=True, targeting_mode="inspect"),
```

**Range value:** Use `10` (a generous value for the look cursor). Phase 13 will clamp range to `player.perception` stat; for Phase 12, a fixed large range is fine. The `move_cursor()` function in `ActionSystem` already enforces the range limit at line 131.

### Pattern 2: Free Action — Skip `end_player_turn` for Inspect Mode

**What:** In `confirm_action()`, check the targeting mode before calling `end_player_turn()`. Inspection is a free action (INV-03) — confirming on a tile must not advance the turn.

```python
# ecs/systems/action_system.py — in confirm_action(), after cancel_targeting():
# FROM:
self.cancel_targeting(entity)
self.turn_system.end_player_turn()
return True
# TO:
mode = targeting.action.targeting_mode
self.cancel_targeting(entity)
if mode != "inspect":
    self.turn_system.end_player_turn()
return True
```

Note: Read `targeting.action.targeting_mode` BEFORE calling `cancel_targeting()` because `cancel_targeting()` removes the `Targeting` component, making `targeting` a dangling reference.

### Pattern 3: Cursor Color by Targeting Mode

**What:** `draw_targeting_ui()` in `RenderSystem` receives the `Targeting` component. Read `targeting.mode` to select the color palette.
**When to use:** Combat mode uses yellow; inspect mode uses cyan.

```python
# ecs/systems/render_system.py — in draw_targeting_ui():
# Define colors based on mode
if targeting.mode == "inspect":
    range_color = (0, 255, 255, 50)   # Transparent cyan for range overlay
    cursor_color = (0, 255, 255)       # Cyan cursor box (INV-03, UI-03)
else:
    range_color = (255, 255, 0, 50)    # Transparent yellow for combat
    cursor_color = (255, 255, 0)       # Yellow cursor box

# Replace the hardcoded (255, 255, 0, 50) and (255, 255, 0) with these variables.
```

### Pattern 4: Header Text by Targeting Mode

**What:** `draw_header()` in `UISystem` currently shows "Targeting..." for all `GameStates.TARGETING`. To show "Investigating..." for inspect mode (UI-02), query the active `Targeting` component for the player entity.
**When to use:** Only when game state is `TARGETING`.

```python
# ecs/systems/ui_system.py — in draw_header(), TARGETING branch:
# FROM:
elif self.turn_system.current_state == GameStates.TARGETING:
    turn_str = "Targeting..."
    turn_color = (100, 255, 255)
# TO:
elif self.turn_system.current_state == GameStates.TARGETING:
    # Check mode from active Targeting component
    try:
        targeting = esper.component_for_entity(self.player_entity, Targeting)
        if targeting.mode == "inspect":
            turn_str = "Investigating..."
        else:
            turn_str = "Targeting..."
    except KeyError:
        turn_str = "Targeting..."
    turn_color = (100, 255, 255)
```

### Pattern 5: Description.get() Accepts stats=None

**What:** The prior decision states `Description.get()` must accept `stats=None` to handle portals/corpses without crash. This is needed for Phase 14 but the guard must exist by Phase 12 to prevent future breakage.
**When to use:** Any call to `Description.get()` where the entity may lack a `Stats` component.

```python
# ecs/components.py — update Description.get():
def get(self, stats=None) -> str:
    if stats is not None and self.wounded_text and stats.max_hp > 0:
        if stats.hp / stats.max_hp <= self.wounded_threshold:
            return self.wounded_text
    return self.base
```

### Anti-Patterns to Avoid

- **Reading `targeting.action.targeting_mode` AFTER `cancel_targeting()`:** `cancel_targeting()` removes the `Targeting` component. Always read `.mode` or `.action.targeting_mode` from the local `targeting` variable before calling `cancel_targeting()`.
- **Adding a new `GameStates.INSPECTING`:** The prior decision locks this: reuse `GameStates.TARGETING` with `targeting_mode="inspect"`. Do not add a new state.
- **Calling `end_player_turn()` for inspect:** Investigation is a free action. Calling `end_player_turn()` would cause enemy turns to fire (failing success criterion 3).
- **Rendering description panel in RenderSystem:** The prior decision states description panel is rendered in `UISystem` only. `RenderSystem` draws inside the viewport clip boundary. Description text must not be drawn inside `draw_targeting_ui()`.
- **Using a large default range without checking map bounds:** `move_cursor()` already clamps to `targeting.range` and checks visibility. Setting `range=10` is safe — the clamp logic is already in place.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inspect cursor movement | Custom cursor entity or new input path | Existing `move_cursor()` in `ActionSystem` | Already handles range clamping and visibility check; called from existing `handle_targeting_input()`. |
| Inspect mode state | New `GameStates.INSPECTING` | `GameStates.TARGETING` + `targeting_mode="inspect"` | Prior decision locked. State machine is already wired in `game_states.py` line 156. |
| Cancel-and-restore logic | Custom escape handler | Existing `cancel_targeting()` | Already removes `Targeting` component and sets `PLAYER_TURN`. No turn is consumed. |
| Auto-target finding | Custom visibility search | Existing `find_potential_targets()` | For inspect mode, `auto` target finding is irrelevant (inspect starts at player position). The existing `start_targeting()` path with `mode="inspect"` (not "auto") skips target finding. |

**Key insight:** The targeting system was built to be mode-agnostic. The `mode` field on `Targeting` already exists precisely to allow different behaviors per mode. Phase 12 only needs to fill in the few spots that were left as "Targeting..." / yellow regardless of mode.

---

## Common Pitfalls

### Pitfall 1: Range 0 blocks cursor movement immediately
**What goes wrong:** If `Action(name="Investigate")` keeps `range=0` (current default), `move_cursor()` in `ActionSystem` computes `dist > targeting.range` as `dist > 0` which is true for any movement, blocking the cursor immediately.
**Why it happens:** `range=0` is the default for non-targeting actions. The cursor starts at `(origin_x, origin_y)` but cannot move anywhere.
**How to avoid:** Set `range=10` (or another reasonable positive value) in the Investigate Action definition in `party_service.py`. Phase 13 will further constrain this to `player.perception`.
**Warning signs:** Cursor appears at player position but arrow keys do nothing.

### Pitfall 2: Reading mode after cancel_targeting() removes component
**What goes wrong:** `confirm_action()` calls `cancel_targeting(entity)` which calls `esper.remove_component(entity, Targeting)`. If you then try to read `targeting.mode` (or any field from the formerly-attached component), it may work in CPython due to object lifetime but is semantically incorrect and fragile.
**Why it happens:** The local `targeting` variable is a reference to the dataclass instance. After `remove_component`, esper no longer holds the reference but the local variable may still point to the object. However, relying on this is undefined behavior in future esper versions.
**How to avoid:** Read `mode = targeting.action.targeting_mode` into a local variable BEFORE calling `cancel_targeting(entity)`.
**Warning signs:** AttributeError or unexpected behavior when confirming inspect action.

### Pitfall 3: start_targeting() checks mana even for free inspect action
**What goes wrong:** `start_targeting()` in `ActionSystem` has `if action.cost_mana > stats.mana: return False`. For Investigate, `cost_mana=0` (default) and player always has mana >= 0, so this passes. No problem in practice.
**Why it happens:** The mana check is generic. Since Investigate has `cost_mana=0` it never blocks entry.
**How to avoid:** No change needed. Document that Investigate must keep `cost_mana=0`.
**Warning signs:** Investigate action silently fails to enter targeting mode (would only happen if `cost_mana` is accidentally set).

### Pitfall 4: UISystem needs Targeting import
**What goes wrong:** `UISystem` currently imports `ActionList, Stats, Targeting` from `ecs.components` (line 4). The `Targeting` import already exists — but the `draw_header()` code doesn't currently USE it. Adding the `esper.component_for_entity(self.player_entity, Targeting)` call is safe because the import is already there.
**Why it happens:** Not a problem — just a confirmation that no new import is needed.
**How to avoid:** Verify the existing `from ecs.components import ActionList, Stats, Targeting` import is on line 4 of `ui_system.py`. It is.
**Warning signs:** NameError for `Targeting` if import was somehow removed.

### Pitfall 5: confirm_action() for inspect — Enter key behavior
**What goes wrong:** In `handle_targeting_input()` in `game_states.py`, pressing Enter calls `confirm_action()`. For inspect mode in Phase 12, confirming on a tile should be a no-op (Phase 14 will add actual inspection output). If `confirm_action()` calls `end_player_turn()` for inspect mode, pressing Enter during investigation causes enemy turns.
**Why it happens:** `confirm_action()` always calls `end_player_turn()` currently.
**How to avoid:** Apply Pattern 2 (skip `end_player_turn` when `mode == "inspect"`). After the fix, pressing Enter in inspect mode cancels targeting and returns to play with no turn consumed — which is acceptable for Phase 12 since Phase 14 adds the actual output.
**Warning signs:** Pressing Enter during investigation causes enemy turns to fire (round counter increments).

---

## Code Examples

Verified patterns from the existing codebase:

### Existing targeting flow (confirmed working for combat)
```python
# game_states.py lines 156-159 — TARGETING state gate (no change needed)
if self.turn_system.current_state == GameStates.TARGETING:
    self.handle_targeting_input(event)
elif self.turn_system.is_player_turn():
    self.handle_player_input(event)
```

### Existing handle_player_input — Enter key triggers start_targeting
```python
# game_states.py lines 177-179 — no change needed
elif event.key == pygame.K_RETURN:
    selected_action = action_list.actions[action_list.selected_idx]
    if selected_action.requires_targeting:
        self.action_system.start_targeting(self.player_entity, selected_action)
```

### Existing start_targeting — mode is set from action
```python
# action_system.py lines 55-82
# The Targeting component is created with mode=action.targeting_mode
# For "inspect" mode, action.targeting_mode == "inspect", so targeting.mode == "inspect"
# The "auto" target-finding branch is SKIPPED for non-"auto" modes
targeting = Targeting(
    origin_x=pos.x, origin_y=pos.y,
    target_x=pos.x, target_y=pos.y,
    range=action.range,
    mode=action.targeting_mode,   # "inspect" for Investigate
    action=action
)
if action.targeting_mode == "auto":
    # ... find targets ... (skipped for inspect)
    pass
esper.add_component(entity, targeting)
self.turn_system.current_state = GameStates.TARGETING
```

### Existing cancel_targeting — free action path
```python
# action_system.py lines 182-185 — no change needed
def cancel_targeting(self, entity):
    if esper.has_component(entity, Targeting):
        esper.remove_component(entity, Targeting)
    self.turn_system.current_state = GameStates.PLAYER_TURN
# Note: does NOT call end_player_turn() — escape cancel is always free
```

### Existing draw_targeting_ui — hardcoded colors to be parameterized
```python
# render_system.py lines 108-110, 121 — these two locations get color variables
s.fill((255, 255, 0, 50))  # → range_color tuple (mode-dependent)
pygame.draw.rect(surface, (255, 255, 0), ...)  # → cursor_color (mode-dependent)
```

### Existing UISystem TARGETING header — to be extended
```python
# ui_system.py lines 44-46 — replace with mode-aware version
elif self.turn_system.current_state == GameStates.TARGETING:
    turn_str = "Targeting..."
    turn_color = (100, 255, 255)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Investigate action does nothing | Investigate enters inspect targeting mode | Phase 12 | Player can enter, navigate, and cancel look mode |
| All targeting uses yellow cursor | Inspect mode uses cyan, combat uses yellow | Phase 12 | Visual distinction between investigation and combat targeting |
| Header always says "Targeting..." | Header says "Investigating..." in inspect mode | Phase 12 | Distinct UI feedback for investigation mode |

---

## Open Questions

1. **What should pressing Enter (confirm) do in inspect mode in Phase 12?**
   - What we know: Phase 14 adds actual inspection output. Phase 12 has no output yet.
   - What's unclear: Should Enter in inspect mode (Phase 12) be a no-op (cursor stays), a cancel (returns to play), or emit a log message stub?
   - Recommendation: Make Enter cancel targeting and return to play (same as Escape) with no turn consumed. This satisfies INV-03 (free action), gives the player a clear way to exit, and Phase 14 will replace the behavior with actual output. Simplest correct behavior.

2. **What range value to use for Investigate in Phase 12?**
   - What we know: Phase 13 will clamp range to `player.perception` stat (currently 10 for the player). A fixed `range=10` in Phase 12 matches the perception value and causes no visible difference once Phase 13 is implemented.
   - Recommendation: Use `range=10` in Phase 12. Phase 13 will make it dynamic.

3. **Should the range highlight (transparent overlay) be drawn for inspect mode?**
   - What we know: The cyan range overlay would show the inspection range visually. This matches success criterion 1 (cursor appears) and 5 (cyan color for investigation).
   - Recommendation: Yes, draw the range highlight in cyan. It visually clarifies the investigation range. `draw_targeting_ui()` already draws range highlight; just change the color.

---

## Sources

### Primary (HIGH confidence)
- `/home/peter/Projekte/rogue_like_rpg/services/party_service.py` — Confirmed: Investigate Action exists at line 21 with `requires_targeting=False`, `range=0` (defaults).
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/action_system.py` — Confirmed: `start_targeting()` uses `action.targeting_mode` for `Targeting.mode`; `confirm_action()` always calls `end_player_turn()`; `cancel_targeting()` does not consume turn.
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/render_system.py` — Confirmed: `draw_targeting_ui()` hardcodes `(255,255,0)` yellow at two locations (range overlay line 109, cursor box line 121).
- `/home/peter/Projekte/rogue_like_rpg/ecs/systems/ui_system.py` — Confirmed: header shows "Targeting..." for all `TARGETING` states; `Targeting` already imported; player_entity available as `self.player_entity`.
- `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — Confirmed: `Targeting` has `mode: str` field; `Description.get(stats)` has no `None` guard.
- `/home/peter/Projekte/rogue_like_rpg/game_states.py` — Confirmed: `handle_player_input()` dispatches to `start_targeting()` when `requires_targeting=True`; `handle_targeting_input()` handles all arrow keys, Escape, Enter — no changes needed here.
- `/home/peter/Projekte/rogue_like_rpg/config.py` — Confirmed: `GameStates.TARGETING` exists; no new state needed.
- `python -m pytest tests/verify_description.py -v` — Confirmed: 7/7 tests pass; Phase 11 complete.

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` — Phase 12 requirements INV-01, INV-03, INV-04, UI-02, UI-03 and success criteria 1-5 confirmed.
- `.planning/phases/11-investigation-preparation/11-01-VERIFICATION.md` — Confirmed all Phase 11 truths verified; `Description` component, `Targeting.mode` field, `draw_targeting_ui()` all in place.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; pure in-place edits to existing Python files.
- Architecture: HIGH — all mechanisms already exist; only filling in mode-specific branches.
- Pitfalls: HIGH — identified from direct code audit; range=0 default and post-cancel read order are concrete, verifiable issues.
- Color values: HIGH — `(0, 255, 255)` for cyan, `(255, 255, 0)` for yellow confirmed against pygame color convention.

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable codebase; no external dependencies)
