## 2024-05-24 - Actionable Empty States & Context-Aware Hints
**Learning:** Generic 'Empty' messages leave users stuck. Displaying keyboard hints for actions that are currently impossible (like dropping an item from an empty inventory) causes confusion. Providing actionable advice in empty states (e.g., 'press [G] to pick up') and hiding invalid key hints reduces friction and cognitive load.
**Action:** Always pair empty states with a call-to-action on how to populate them, and dynamically hide footer keyboard hints for actions that cannot be performed in the current state.
