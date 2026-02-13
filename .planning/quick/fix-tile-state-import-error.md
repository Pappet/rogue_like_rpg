---
phase: quick-fix
plan: 02
type: execute
wave: 1
depends_on: []
files_modified: [game_states.py]
autonomous: true

must_haves:
  truths:
    - "game_states.py imports VisibilityState correctly"
    - "game_states.py does not contain redundant local imports for VisibilityState"
    - "game_states.py does not attempt to import the non-existent TileState"
  artifacts:
    - path: "game_states.py"
      provides: "Game state logic with correct map imports"
---

<objective>
Fix the ImportError in game_states.py by correcting the import from map.tile.

Purpose: Allow the game to start without ImportErrors.
Output: Updated game_states.py.
</objective>

<execution_context>
@/home/peter/.gemini/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/PROJECT.md
@game_states.py
@map/tile.py
</context>

<tasks>

<task type="auto">
  <name>Correct imports in game_states.py</name>
  <files>game_states.py</files>
  <action>
    - Change line 17: `from map.tile import TileState` to `from map.tile import VisibilityState`.
    - Remove line 372: `from map.tile import VisibilityState` (it's redundant once moved to top level).
    - Ensure all usages of `VisibilityState` in `game_states.py` are consistent.
  </action>
  <verify>
    Run `python3 main.py` or a verification script to ensure no ImportErrors occur.
  </verify>
  <done>
    game_states.py imports VisibilityState correctly and starts without error.
  </done>
</task>

</tasks>

<verification>
Ensure the game launches without ImportError related to TileState.
</verification>

<success_criteria>
1. VisibilityState is imported at the top of game_states.py.
2. TileState import is removed.
3. Redundant local import in WorldMapState.draw is removed.
</success_criteria>

<output>
After completion, create `.planning/quick/fix-tile-state-import-error-SUMMARY.md`
</output>
