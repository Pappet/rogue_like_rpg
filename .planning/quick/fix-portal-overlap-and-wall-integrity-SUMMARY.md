# Quick Fix: Fix Portal Overlap and Wall Integrity Summary

## Objective
Ensure that portals (stairs up/down) do not overlap on the same layer and that house portals do not "break" (replace) wall tiles.

## Changes

### services/map_service.py
- **Staggered Stairs:** Updated `add_house_to_map` to use alternating coordinates for stairs based on floor parity.
    - Even Floors: Up at `(w-2, 2)`, Down at `(2, 2)`.
    - Odd Floors: Up at `(2, 2)`, Down at `(w-2, 2)`.
    - This ensures that if a floor has both Up and Down stairs, they are at opposite sides of the room.
- **Wall Integrity:**
    - Removed `place_door` call in `add_house_to_map`.
    - Removed code in `create_village_scenario` that set wall tiles to `+`.
- **Portal Repositioning:**
    - Village-to-House portals moved to `(door_vx, door_vy + 1)` (one tile south of the house shell).
    - House-to-Village portals moved to `(hi // 2, hj - 2)` (one tile north of the interior south wall).
    - Target coordinates for these portals updated to ensure players land on the new portal positions.

## Verification Results
- Verified that `add_house_to_map` no longer modifies the ground layer to create door openings.
- Verified that stair positions are calculated dynamically per layer to avoid collisions.
- Confirmed that village house shells remain solid `#` blocks.

## Commits
- [placeholder-hash]: fix(map): prevent portal overlap and preserve wall integrity

## Self-Check: PASSED
