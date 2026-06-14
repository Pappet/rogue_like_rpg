## 2024-05-24 - Esc/Close Hotkey Consistency
**Learning:** Found inconsistent phrasing in window footer hints. Some use `[Esc/C] Close`, some use `[Esc] Close`, `[Esc] Leave`, `[Esc] Cancel`. The phrasing in keyboard hints is not consistent. Consistency helps build muscle memory and reduces mental load.
**Action:** Let's standardize the close/cancel message to `[Esc] Close` for standard windows and `[Esc] Cancel` for modal dialogues. For windows opened with a hotkey, the format `[Esc/KEY] Close` is good if we support toggling. Wait, character.py has `[Esc/C] Close`. But inventory has `[Esc] Close` even though it can be opened/closed with `I`. Wait, `[Esc]` does not support toggling in `inventory.py`. I should look into this.

## 2024-05-24 - Use vs Confirm
**Learning:** In the inventory window, `[Enter/U] Use` is used, but what if the item is not usable? Or what if it's equippable?
**Action:** Add contextual text or rely on consistent bindings.
## 2024-05-24 - Dynamic Action Hints
**Learning:** Found that the inventory window shows `[Enter/U] Use [E] Equip` for all items, even if they can only be used or only be equipped. This causes confusion. It would be a great UX improvement to conditionally show `[Enter/U] Use` or `[Enter/E] Equip` based on the selected item's components (`Consumable` and `Equippable`).
**Action:** Let's update `inventory.py` to inspect the selected item and dynamically update the hint text. If it's a `Consumable`, show `[Enter/U] Use`. If it's an `Equippable`, show `[Enter/E] Equip` or `[Enter/E] Unequip`.
