# Feature Research

**Domain:** Item & inventory system for tile-based rogue-like RPG (ECS/Python/esper)
**Researched:** 2026-02-15
**Confidence:** HIGH — derived from codebase analysis, rogue-like design canon (NetHack, DCSS, Brogue, Angband lineage), and ECS pattern literature. WebSearch unavailable; all claims grounded in existing codebase hooks or well-established rogue-like conventions (HIGH confidence).

---

## Context: Existing System Hooks

The following already exist and are the integration surface for every item/inventory feature:

| Existing System | What It Provides | How Item System Uses It |
|-----------------|-----------------|-------------------------|
| `Inventory` component (`ecs/components.py:51`) | `items: List` stub — entity IDs or item data | Promote to typed list of ECS entity IDs |
| `Stats` component | `power`, `defense`, `hp`, `max_hp`, `mana`, `max_mana` | Equipment modifies effective stats dynamically |
| `SpriteLayer.ITEMS = 3` (`config.py:37`) | Render layer already reserved for item sprites | Items placed on map render at this layer |
| `EntityFactory` + `EntityRegistry` | JSON-driven entity creation with conditional component attachment | Item templates loaded from JSON, `ItemFactory` mirrors this pattern |
| `DeathSystem` | Fires `entity_died` event, transforms corpse | Loot drop hook — `on_entity_died` spawns loot entities at corpse position |
| `ActionSystem.perform_action()` | Turn-costing action dispatch | "Pick up", "Use item", "Drop item" are actions dispatched here |
| `Action` / `ActionList` components | Player action menu in `UISystem` sidebar | Item-related actions ("Pick Up", "Open Inventory") appear here |
| `GameStates` enum | `PLAYER_TURN`, `ENEMY_TURN`, `TARGETING` | New `INVENTORY` state needed for inventory screen |
| `Description` component | Inspection text for entities | Items carry `Description` — shown when inspecting or examining in inventory |
| `esper.dispatch_event("log_message", ...)` | Message log with color markup | All item interactions narrated through existing log |
| `UISystem` (header/sidebar/log layout) | `SCREEN_WIDTH=800`, `HEADER_HEIGHT=48`, `SIDEBAR_WIDTH=160`, `LOG_HEIGHT=140` | Inventory UI must fit within or overlay this layout |

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features any rogue-like player expects. Missing one makes the system feel broken or unfinished.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Item ECS entity** — items are full entities with `Position`, `Renderable`, `Name`, `Description`, `Item` tag components | Every rogue-like has pickable items on the map; if items aren't world entities they can't be seen, inspected, or interacted with | LOW | `SpriteLayer.ITEMS = 3` already reserved. `Item` tag component added to `components.py`. JSON template format mirrors existing `entities.json`. `ItemFactory` mirrors `EntityFactory`. |
| **Pick up (g/comma key)** — player moves onto or confirms pickup of item at their tile; item entity loses `Position`, is added to `Inventory.items` list | Foundational action; without it items are just scenery | LOW | `ActionSystem.perform_action()` handles "Pick Up". Query `esper.get_components(Position, Item)` for same tile as player. Remove `Position` + `Renderable` from item entity (or just `Position` to preserve data). Append entity ID to `Inventory.items`. Log: `"You pick up the [item name]."` Costs one turn. |
| **Inventory screen (i key)** — modal overlay listing all items in inventory by name, navigable with arrow keys | Standard interface for all inventory operations — without it players cannot see what they have | MEDIUM | New `GameStates.INVENTORY` state. Pause turn processing while open. Render list of items by `Name` component, highlight selected. Display selected item's `Description`. Key bindings: arrow keys navigate, `d` drop, `u`/`Enter` use/equip, `Esc` close. Inventory state is a modal that does not advance the turn clock. |
| **Drop item (d in inventory)** — item removed from inventory, re-spawned at player's position as world entity | Paired operation with pickup; players expect to be able to place items back | LOW | Remove entity ID from `Inventory.items`. Re-add `Position(player.x, player.y)` and `Renderable` to item entity. Log: `"You drop the [item name]."` Costs one turn (on close). |
| **Item description / examine (x/Enter in inventory)** — show full `Description` text for selected item | Players need to know what items do before using them; inspect system already proves the pattern | LOW | Read `Description.base` from item entity and render in inventory panel or push to message log. Pattern is identical to `ActionSystem.confirm_action()` inspect mode — reuse. |
| **Equipment slots** — equip wearable items (weapon, armor) to named body slots; equipped items show in a separate equipment panel | Every combat-focused rogue-like has equipment; without slots gear has no mechanical meaning | MEDIUM | `Equipment` component: `slots: dict[str, Optional[int]]` where keys are slot names (`"weapon"`, `"armor"`, `"ring_l"`, `"ring_r"`) and values are item entity IDs or `None`. `Equippable` component on item: `slot: str`. "Equip" action in inventory moves item from `Inventory.items` to `Equipment.slots[slot]`. Only one item per slot — equipping to occupied slot auto-swaps to inventory. |
| **Stat modification from equipment** — equipped items change effective `power` and `defense` during combat | Without this, equipment has no game-mechanical effect | MEDIUM | Two approaches: (A) **Computed stats** — `CombatSystem` sums base `Stats` plus all equipped item bonuses at attack time. (B) **Dirty flag** — when equipment changes, recompute and write to `Stats`. Approach A is safer (no stale state) and fits ECS better. `Equippable` component carries `power_bonus: int`, `defense_bonus: int`. `CombatSystem` queries `Equipment` to sum bonuses. |
| **Consumable items (use/quaff)** — items with one-time effects (healing potion restores HP, scroll triggers effect) | Consumables are the primary tactical resource in rogue-likes; without them items are only gear | MEDIUM | `Consumable` component: `effect: str`, `magnitude: int`. "Use" action in inventory invokes `ItemUseSystem` which dispatches on `effect`. Effects: `"heal"` (restore HP), `"mana_restore"` (restore mana). After use, item entity is deleted from world. Log narrates effect. Costs one turn. |
| **Loot drops from monsters** — monsters drop items on death at their tile | Contextual loot is stated as a project goal; without drops the economy has no source of items | MEDIUM | `LootTable` component on monster entity: list of `(template_id, probability)` pairs. `DeathSystem.on_entity_died()` hook: if entity has `LootTable`, roll each entry, `ItemFactory.create(world, template_id, x, y)` for each successful roll. Wolf drops "wolf_pelt" (high probability), "wolf_fang" (low probability). No gold on wolves. |
| **Weight / carry capacity** — player has a max carry weight; `Item` component carries `weight: float`; cannot pick up when over limit | Weight-based capacity is stated as a project design goal | LOW | `CarryCapacity` component on player: `max_weight: float`, computed `current_weight` property sums `Item.weight` for all entities in `Inventory.items`. Pickup action blocked if `current_weight + item.weight > max_weight`. Log: `"Too heavy to carry."` UI shows current/max weight in inventory screen. |

### Differentiators (Competitive Advantage)

Features that make this system distinctive within the rogue-like design space. These align with the stated project goals.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Material component** — items and world entities carry `Material` component: `material_type: str` (wood, metal, glass, leather, stone, organic) | Simulation-first material interactions (burns, conducts, shatters) differentiate this system from generic stat-swap gear | MEDIUM | `Material` component: `material_type: str`. `MaterialProperties` registry (dict or JSON): maps material to `{"flammable": bool, "conductive": bool, "fragile": bool, "organic": bool}`. Initial use: description flavor ("The wooden club could burn."). Mechanical effects deferred to interaction-specific systems (fire, lightning, impact). |
| **Material interaction rules** — wood burns when exposed to fire, metal conducts electricity, glass shatters on impact | Emergent gameplay from simulation; memorable moments arise from material interactions | HIGH | Requires event-driven interaction system: `ItemInteractionSystem` listens for `"apply_fire"`, `"apply_lightning"`, `"apply_impact"` events. Per-interaction: query `Material.material_type`, look up in `MaterialProperties` registry, apply effect (destroy item if fragile, propagate fire if flammable). Defer to its own phase — HIGH complexity and HIGH dependency on effects/magic systems not yet built. |
| **Contextual loot** — monster loot tables derive from creature biology, not arbitrary treasure pools | Wolves drop pelts and fangs, not gold coins; NPCs carry things they logically would | LOW (loot table data) / MEDIUM (convincing content) | `LootTable` component entries reference item template IDs. Template data in `assets/data/items.json`. Content design is the hard part: each monster type needs a believable `LootTable`. Implementation is LOW complexity; content is MEDIUM ongoing work. |
| **Item inspection in world** — player can use existing "Inspect" action (`targeting_mode="inspect"`) on item tiles to read description before picking up | Reduces "mystery item" frustration; respects the existing investigation system investment | LOW | `ActionSystem.confirm_action()` already lists entities at the target tile with their `Description`. Items are entities with `Description`. No new code needed — item entities with `Name` and `Description` are automatically visible to inspect. |
| **Equipment visual feedback** — equipped items listed in sidebar or HUD panel; currently equipped weapon/armor named | Players need to see their loadout at a glance without opening inventory | LOW | Extend `UISystem.draw_sidebar()` to query `Equipment` component on player entity and render slot names + item names below the action list. Only adds to existing sidebar code. |
| **Identified / unidentified items** — scrolls and potions have unknown names until used or identified | A rogue-like staple that creates information asymmetry and replayability | MEDIUM | `Identified` component (tag). Display name: if `Identified` present, show `Name.name`; otherwise show `Item.unknown_name` (e.g., "Cloudy Potion"). On use, add `Identified` component and log the true name. Requires per-run randomization of `unknown_name` → `true_name` mapping, stored in a `IdentificationService`. Defer to v1.x — adds complexity to base consumable system. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Nested containers (bags-in-bags)** | Players want organization — "put all potions in this bag" | Recursive container logic, drag-and-drop UI, weight accounting through nesting, serialization complexity. Adds several weeks of work for marginal gameplay benefit. Project spec says flat inventory. | Flat `Inventory.items` list with sort/filter in the UI. Categories visible via item type tag on the `Item` component. |
| **Item stacking (20 arrows in one slot)** | Efficient display of large item counts | Stackable items require either duplicate entity management or a `Quantity` component that breaks the "items are full entities" architecture. A `Quantity` component is fine, but "how do you split a stack?" is a full sub-system. | For consumables: simple `Consumable` entity per item (a pouch of 3 potions is 3 entities). For ammo: `Ammo` component with `count: int` on a single entity — this is a targeted exception, not general stacking. |
| **Full item crafting system (combine A + B = C)** | Logical extension of material properties | Crafting requires recipe data, a crafting UI state, combination logic, and an entirely new design space. It is an independent milestone. | Material interactions (wood burns) provide the simulation feel without the crafting UI. Defer crafting to a dedicated milestone after materials work. |
| **Real-time item drag-and-drop UI** | Feels modern and polished | The game is turn-based. Drag-and-drop requires pygame mouse handling, drop targets, hover states, and a fundamentally different UI model from the current keyboard-driven interface. ROI is low. | Keyboard-navigated inventory (arrow keys + key bindings) is the rogue-like convention. Players expect it. It is faster to implement and faster to use in a turn-based context. |
| **Automatic item sorting / management** | Reduces inventory tedium | Auto-management hides information from players; in a simulation-first game, knowing what you carry and deciding what to drop is a core decision. Automating it removes agency. | Sort key (press `s` in inventory to alphabetically sort) is sufficient. Category grouping by item type in display order. |
| **Item durability / repair** | Adds resource pressure and realism | Durability requires tracking per-item degradation, a repair mechanic, and communicating condition to the player. Adds three components (`Durability`, repair actions, UI state) for a mechanic that frustrates more than it engages in short-session rogue-likes. | Material fragility (glass shatters on impact — one-shot destruction) provides consequence without ongoing bookkeeping. |

---

## Feature Dependencies

```
[Item ECS entity (Position, Renderable, Item, Name, Description, Material)]
    └──required by──> Pick up
    └──required by──> Drop item
    └──required by──> Loot drops
    └──required by──> Item inspection in world (free — inspect system already handles it)
    └──required by──> Weight / carry capacity
    └──required by──> Equipment slots
    └──required by──> Consumable items

[Pick up]
    └──requires──> Item ECS entity
    └──requires──> Inventory component (exists as stub — promote to typed list)
    └──requires──> Weight / carry capacity (enforced during pickup)

[Inventory screen (GameStates.INVENTORY)]
    └──requires──> Pick up (items must be in inventory to display)
    └──requires──> Item ECS entity (for Name and Description rendering)
    └──enables──> Drop item
    └──enables──> Equipment slot assignment
    └──enables──> Consumable use

[Equipment slots]
    └──requires──> Inventory screen (equip action initiated from inventory UI)
    └──requires──> Item ECS entity with Equippable component
    └──enables──> Stat modification from equipment

[Stat modification from equipment]
    └──requires──> Equipment slots
    └──requires──> CombatSystem extension (reads Equipment during damage calculation)
    └──modifies──> Stats.power / Stats.defense (computed, not written)

[Consumable items]
    └──requires──> Inventory screen (use action initiated from inventory)
    └──requires──> Item ECS entity with Consumable component
    └──reads──> Stats (for heal/mana targets)

[Loot drops]
    └──requires──> Item ECS entity + ItemFactory
    └──hooks into──> DeathSystem.on_entity_died() (existing event)
    └──requires──> LootTable component on monster entities

[Weight / carry capacity]
    └──requires──> Item component with weight field
    └──gates──> Pick up action

[Material component]
    └──requires──> Item ECS entity (materials live on item entities)
    └──enhances──> Item description (flavor text about material)
    └──enables──> Material interactions (future phase)

[Material interactions]
    └──requires──> Material component
    └──requires──> Effects / fire / lightning systems (NOT YET BUILT — future milestone)
    └──HIGH complexity — own phase
```

### Dependency Notes

- **Item ECS entity is the universal prerequisite.** Everything else depends on items existing as world entities. This is Phase 1 of the milestone.
- **Pick up before inventory screen.** The inventory screen is only meaningful when it can show items that have been picked up. Implement pick up first (even without a full UI), validate with message log output, then build the inventory screen.
- **Equipment requires inventory screen.** Equip/unequip is an action initiated inside the inventory UI. Equipment slots have no entry point without the inventory screen.
- **Stat modification depends on equipment.** Cannot test stat bonuses until the equip action works. Both ship together.
- **Loot drops depend only on ItemFactory, not on inventory.** Drops can be built in parallel with inventory — they produce floor items that the inventory system then consumes.
- **Material interactions are intentionally decoupled.** The `Material` component and registry can be built early (it's just data). The interaction rules (burns/conducts/shatters) require fire and lightning systems that don't exist yet. Plan for `Material` in v1, interactions in v2+.
- **Identified/unidentified items depend on consumables.** Cannot identify an item category that doesn't work yet. Defer.

---

## MVP Definition

### Launch With (v1) — Minimum Viable Item System

The loop: monster dies → drops loot → player picks it up → equips or uses it → combat stats change.

- [ ] **Item ECS entity** — `Item`, `Material`, `Equippable`/`Consumable` as conditional components; JSON template file `assets/data/items.json`; `ItemFactory` mirrors `EntityFactory`. Why essential: everything else requires this.
- [ ] **Pick up** — `g` key while standing on item or in same tile; item removed from world, added to `Inventory.items`; weight checked against `CarryCapacity`. Why essential: core loop entry point.
- [ ] **Weight / carry capacity** — `CarryCapacity` on player; `Item.weight`; pickup blocked when over limit. Why essential: stated design goal; prevents degenerate "carry everything" play.
- [ ] **Loot drops** — `LootTable` on orc entity; `DeathSystem` hook spawns items at death tile; wolf/orc templates get contextual loot. Why essential: items need a source; tests the whole loop.
- [ ] **Inventory screen** — `GameStates.INVENTORY`; modal overlay; navigate with arrow keys; show item name + description; `Esc` to close; `d` to drop. Why essential: players need to see and manage what they carry.
- [ ] **Equipment slots** — `Equipment` component on player; equip/unequip from inventory screen; slot collision swaps item back to inventory. Why essential: gear must have a mechanical home.
- [ ] **Stat modification from equipment** — `CombatSystem` reads `Equipment` and sums `Equippable` bonuses at attack time. Why essential: equipment must affect combat or it is purely cosmetic.
- [ ] **Consumable items (heal)** — `Consumable` component; `"heal"` effect restores HP; item deleted on use; logged. Why essential: health potions are the simplest test of the consumable pipeline.

### Add After Validation (v1.x)

- [ ] **Material component + flavor descriptions** — add `Material` to item entities; update `Description` to mention material type; `MaterialProperties` registry data. Trigger: once v1 is stable and the simulation feel needs enhancement.
- [ ] **Identified/unidentified items** — `IdentificationService` with per-run name shuffling; `unknown_name` on `Item`; reveal on use. Trigger: once consumables work and replayability is desired.
- [ ] **Equipment visual feedback in sidebar** — extend `UISystem.draw_sidebar()` to show currently equipped weapon and armor. Trigger: once equipment slots work and the HUD feels incomplete.
- [ ] **Additional consumable effects** — `"mana_restore"`, `"poison"`, `"teleport"`. Trigger: once the heal pipeline is confirmed working.

### Future Consideration (v2+)

- [ ] **Material interaction rules** — wood burns, metal conducts, glass shatters. Requires fire/lightning/impact event systems that do not exist. Defer until effects systems are built.
- [ ] **Crafting** — combine items to create new items. Independent milestone. Defer.
- [ ] **Item cursing / blessing** — equipment can be cursed (cannot remove) or blessed (enhanced effect). Adds depth but requires additional UI affordances (show curse status) and content design.

---

## Feature Prioritization Matrix

| Feature | Player Value | Implementation Cost | Priority |
|---------|--------------|---------------------|----------|
| Item ECS entity (templates + factory) | HIGH | LOW | P1 |
| Pick up action | HIGH | LOW | P1 |
| Weight / carry capacity | HIGH | LOW | P1 |
| Loot drops (DeathSystem hook) | HIGH | LOW | P1 |
| Inventory screen (GameStates.INVENTORY) | HIGH | MEDIUM | P1 |
| Equipment slots | HIGH | MEDIUM | P1 |
| Stat modification from equipment | HIGH | LOW (given slots) | P1 |
| Consumable items (heal) | HIGH | LOW | P1 |
| Material component + flavor | MEDIUM | LOW | P2 |
| Equipment feedback in sidebar | MEDIUM | LOW | P2 |
| Additional consumable effects | MEDIUM | LOW | P2 |
| Identified/unidentified items | MEDIUM | MEDIUM | P2 |
| Material interaction rules | HIGH (long-term) | HIGH | P3 |
| Crafting | HIGH (long-term) | HIGH | P3 |
| Item cursing / blessing | MEDIUM | MEDIUM | P3 |

**Priority key:**
- P1: Must have — the item loop does not close without these
- P2: Should have — adds depth; add once P1 is stable
- P3: Nice to have — plan now, build later

---

## System Impact Analysis

Changes required to existing systems (not purely new code):

| Existing System | Change Required | Risk |
|-----------------|----------------|------|
| `ecs/components.py` | Promote `Inventory.items` from `List` to `List[int]` (entity IDs); add `Item`, `Equippable`, `Consumable`, `Material`, `LootTable`, `CarryCapacity`, `Equipment` components | LOW — additive only; `Inventory` already exists as stub |
| `config.py` | Add `GameStates.INVENTORY` to enum | LOW — additive |
| `ecs/systems/death_system.py` | Add loot drop hook in `on_entity_died()` — check for `LootTable`, call `ItemFactory` | LOW — adding to existing handler, not changing existing logic |
| `ecs/systems/combat_system.py` | Sum `Equippable` bonuses from `Equipment` slots at attack time | LOW — additive read before existing damage formula |
| `ecs/systems/action_system.py` | Add `"Pick Up"` and `"Open Inventory"` to `perform_action()` dispatch | LOW — additive case |
| `ecs/systems/ui_system.py` | Add inventory screen render; optionally extend sidebar with equipment summary | MEDIUM — new render path, new game state handling |
| `assets/data/entities.json` | Add `loot_table` array to orc template | LOW — additive JSON field; `EntityFactory` uses conditional component attachment already |
| `game_states.py` | Handle `GameStates.INVENTORY` in `get_event()` — inventory key bindings | MEDIUM — new state event handling |

---

## Sources

- Direct codebase analysis: `ecs/components.py`, `ecs/systems/combat_system.py`, `ecs/systems/death_system.py`, `ecs/systems/action_system.py`, `ecs/systems/ui_system.py`, `entities/entity_factory.py`, `entities/entity_registry.py`, `config.py`, `assets/data/entities.json`, `game_states.py`
- Rogue-like inventory conventions: NetHack, DCSS (Dungeon Crawl Stone Soup), Brogue design — pick-up/drop/equip/use as table stakes; identified/unidentified items as differentiator; no nested containers — universally observed in the genre (HIGH confidence, well-established canon)
- ECS item-as-entity pattern: standard ECS design — items as entities rather than abstract data structures allows position, rendering, inspection, and interaction via the same component queries used for all other entities (HIGH confidence, directly demonstrated in existing codebase)
- Weight-based capacity vs slot-count: project specification explicitly states weight-based over slot-count (cited as design goal in milestone context)
- Contextual loot: project specification explicitly names "wolves drop pelts, not gold" — loot tables keyed to creature type, not generic treasure pools

---

*Feature research for: item & inventory system — rogue-like RPG (ECS/Python/esper)*
*Researched: 2026-02-15*
