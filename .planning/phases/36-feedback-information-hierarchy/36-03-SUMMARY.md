# Phase 36 Plan 03: Examine Mode Tooltips Summary

Implemented a dedicated Examine Mode that allows players to inspect any visible entity or tile on the map, providing detailed tooltips with name, health, stats, and descriptions.

## Key Changes

### Interactions & State
- **EXAMINE State**: Added `GameStates.EXAMINE` to manage the lifecycle of inspection. In this state, player movement is blocked, and the directional keys control a cyan examination cursor.
- **Input Integration**: Mapped the 'x' key to enter Examine Mode. ESC correctly exits the mode and clears any active tooltips.
- **Cursor Logic**: Implemented `handle_examine_input` in the `Game` class to handle cursor movement and trigger tooltip updates without advancing the game turn.

### UI & Feedback
- **TooltipWindow**: A new stateful modal in the `UIStack` that renders a multi-line information box.
- **Dynamic Content**: Tooltips automatically update based on the entity under the cursor, displaying:
    - Name and Sprite.
    - HP bar and current/max HP values.
    - Effective Stats (POW, DEF, PER, INT).
    - Entity Description (HP-aware).
    - Item weight (for portable items).
- **Intelligent Positioning**: The tooltip box dynamically repositions itself to avoid screen edges and the message log area, ensuring it never obscures the cursor or important HUD elements.

## Verification Results
- **Visual Check**: Cyan cursor correctly highlights the target tile. Tooltip appears immediately and is readable.
- **Functional Check**: Multiple entities on the same tile are handled. HP bars reflect current health accurately.
- **Bug Fix**: Resolved an `AttributeError` in `EffectiveStats` lookup and a state-sticking bug where Examine Mode wouldn't exit properly.

## Decisions
- Chose to use the `UIStack` for tooltips to leverage the existing modal rendering and input priority infrastructure.
- Decided to make Examine a "free action" that does not advance the world clock, encouraging players to use it frequently for tactical awareness.
