## 2024-05-24 - Surface Item Value in Tooltips and Descriptions
**Learning:** Exposing hidden/existing item data (like `Value`) in tooltips and detailed views significantly reduces the cognitive load of having to pick up an item to know what it's worth.
**Action:** When adding new item properties that affect player decision-making, ensure they are surfaced in all relevant UI contexts (inventory details, examine tooltips).

## 2025-02-28 - Surface Output Details in Crafting Menu
**Learning:** Players need to see the output details of an item (description, weight, value) in the crafting menu *before* crafting it, saving them the cognitive load of having to recall item values, check tooltips elsewhere, or craft the item just to find out.
**Action:** When creating interfaces where an action consumes resources to create an entity (like crafting or merchants), ensure the potential output entity has its detailed data visibly surfaced prior to the transaction. Remember to grow the panel height when adding a line, so the extra text stays inside the inset frame.

## 2024-05-24 - Dynamic Footer Hints Prevent Frustration
**Learning:** Displaying keyboard shortcuts (like `[Enter] Buy` or `[Enter] Craft`) when the action is actually invalid (due to insufficient gold or materials) leads to player frustration and pressing keys without feedback.
**Action:** Always make footer interaction hints context-aware. If an item cannot be bought, crafted, or interacted with, hide the corresponding keyboard hint to cleanly communicate the action's unavailability. Name the concrete action (Accept / Turn in) rather than an ambiguous combined label.
