# Phase 35 Plan 03: Viewport Resizing & HUD Cleanup Summary

Successfully expanded the game viewport to the full width of the screen and refactored the HUD for a cleaner, more immersive experience.

## Key Changes

### Viewport Expansion
- **Sidebar Removal**: Set `SIDEBAR_WIDTH = 0` in `config.py`, reclaiming 220px of horizontal space.
- **Dynamic Camera**: Updated `Camera` and `GameController` to automatically use the full screen width for viewport calculations.
- **Rendering Refactor**: Ensured `RenderSystem` and `DebugRenderSystem` correctly clip and draw to the expanded map area.

### HUD Refactor
- **Compact Header**: Consolidated all critical game information (HP, Mana, Round, Clock) into the top header.
- **Hotbar Visualization**: Implemented a visual 1-9 hotbar in the header, displaying active quick-slots and their mana availability.
- **Improved Alignment**: Used relative positioning and the `LayoutCursor` to ensure HUD elements remain balanced and readable across different screen widths.

### Cleanup
- **Legacy Removal**: Removed the monolithic `draw_sidebar` logic from `UISystem`.
- **System Synchronization**: Verified that viewport-dependent systems (Visibility, Lighting) adapt correctly to the new dimensions.

## Technical Details
- **Modified Files**: `config.py`, `main.py`, `game_states.py`, `ecs/systems/ui_system.py`, `components/camera.py`.
- **Commits**:
    - `d5b53db`: feat(35-03): expand game viewport to full screen width
    - `2bd3ca4`: feat(35-03): refactor UISystem for compact HUD

## Verification Results
- **Visual Check**: Map fills the full width. HP/Mana/Clock are clearly visible in the header.
- **Modal Check**: Inventory and Character windows are centered on the new 1280px width.
- **Functional Check**: Hotbar display updates correctly when actions are used.

## Decisions
- Chose to integrate the Hotbar directly into the header to keep the bottom of the screen focused on the Message Log.
- Maintained the top-left positioning for Round/Clock and top-right for Stats to match standard RPG conventions.
