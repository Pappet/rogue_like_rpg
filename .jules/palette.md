## 2024-05-24 - Surface Item Value in Tooltips and Descriptions
**Learning:** Exposing hidden/existing item data (like `Value`) in tooltips and detailed views significantly reduces the cognitive load of having to pick up an item to know what it's worth.
**Action:** When adding new item properties that affect player decision-making, ensure they are surfaced in all relevant UI contexts (inventory details, examine tooltips).

## 2025-02-28 - Surface Output Details in Crafting Menu
**Learning:** Players need to see the output details of an item (description, weight, value) in the crafting menu *before* crafting it, saving them the cognitive load of having to recall item values, check tooltips elsewhere, or craft the item just to find out.
**Action:** When creating interfaces where an action consumes resources to create an entity (like crafting or merchants), ensure the potential output entity has its detailed data visibly surfaced prior to the transaction. Remember to grow the panel height when adding a line, so the extra text stays inside the inset frame.

## 2024-05-24 - Dynamic Footer Hints Prevent Frustration
**Learning:** Displaying keyboard shortcuts (like `[Enter] Buy` or `[Enter] Craft`) when the action is actually invalid (due to insufficient gold or materials) leads to player frustration and pressing keys without feedback.
**Action:** Always make footer interaction hints context-aware. If an item cannot be bought, crafted, or interacted with, hide the corresponding keyboard hint to cleanly communicate the action's unavailability. Name the concrete action (Accept / Turn in) rather than an ambiguous combined label.

## 2026-06-20 - Show State in the List, Not Just the Footer
**Learning:** Hiding a footer hint when an action is invalid tells the player *that* something is off, but not *which* row. Carrying the same state into the list itself (dimming unaffordable goods, colouring the price red) lets the player scan affordability at a glance instead of selecting each row to find out.
**Action:** When an action's validity varies per list entry, reflect it on the entry (dim/recolour), not only in the shared footer.

## 2026-06-20 - Prefer a Bar Over a Number for Magnitudes
**Learning:** A bare readout like "Weight: 9.0/10.0 kg" forces the player to read and compare two numbers; a coloured fill bar (green → amber → red) communicates "nearly full / over the limit" instantly.
**Action:** For bounded magnitudes (carry load, HP, progress), draw a `theme.draw_bar` with a threshold colour instead of, or alongside, the raw numbers. Keep the same physical facts (Material/Weight/Value) consistent across every surface that shows an item (inventory, crafting, examine tooltip).

## 2024-06-26 - Surface Base Value in Trade Menu
**Learning:** Players benefit from seeing an item's base value alongside the buy/sell price in trade menus to gauge whether a merchant is giving them a fair deal. Showing a raw 0-weight for weightless items clutters the UI unnecessarily.
**Action:** Always surface baseline reference values (like item value) next to dynamically calculated values (like trade prices), and omit properties that are zero (like weight) to declutter detail panes.

## 2026-06-21 - Actionable Empty States and Context-Aware Hints
**Learning:** Displaying non-actionable empty states (e.g., 'There is nothing here to pick up.') and generic footer hints (e.g., '[Enter] Take' when there are no items) increases cognitive load and frustration.
**Action:** For Pygame UI windows, follow the convention of making empty states actionable (providing guidance on how to populate them) and making footer keyboard hints context-aware by dynamically hiding invalid inputs.
## 2024-10-25 - Carry Capacity Visual Indicator
**Learning:** Displaying carry capacity as static text requires the user to mentally compute their current load, creating unnecessary cognitive overhead.
**Action:** Replace static magnitude/capacity numbers with visual progress bars (e.g., `theme.draw_bar`) with color thresholds (green -> amber -> red) for instant visual feedback on limits.
