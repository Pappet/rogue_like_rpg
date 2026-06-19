## 2024-05-24 - Surface Item Value in Tooltips and Descriptions
**Learning:** Exposing hidden/existing item data (like `Value`) in tooltips and detailed views significantly reduces the cognitive load of having to pick up an item to know what it's worth.
**Action:** When adding new item properties that affect player decision-making, ensure they are surfaced in all relevant UI contexts (inventory details, examine tooltips).

## 2024-05-24 - Dynamic Footer Hints Prevent Frustration
**Learning:** Displaying keyboard shortcuts (like `[Enter] Buy` or `[Enter] Craft`) when the action is actually invalid (due to insufficient gold or materials) leads to player frustration and clicking/pressing without feedback.
**Action:** Always make footer interaction hints context-aware. If an item cannot be bought, crafted, or interacted with, hide the corresponding keyboard hint to cleanly communicate the action's unavailability.
