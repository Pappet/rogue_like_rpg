# Quick Task: Fix ActionSystem World Attribute Summary

Resolved the `AttributeError: 'ActionSystem' object has no attribute 'world'` that occurred during item inspection.

## Key Changes
- Modified `ecs/systems/action_system.py`: Replaced `self.world` with `esper` in `confirm_action` when calling `get_detailed_description`.
- Modified `tests/verify_inspection_output.py`: Updated the test to correctly handle multi-line string comparison for inspection output, matching the current implementation's format.

## Results
- Item inspection on the ground no longer crashes.
- Inspection output correctly shows detailed item information (name, description, material, weight).
- Regression tests for inspection output are passing.
