# Project Research Summary

**Project:** Rogue-like RPG — Item & Inventory System (v1.4 milestone)
**Domain:** ECS item/inventory system on Python/PyGame/esper
**Researched:** 2026-02-15
**Confidence:** HIGH

## Executive Summary

The v1.4 milestone adds a full item and inventory system to an existing ECS rogue-like built on Python 3.13, pygame 2.6.1, and esper 3.7. The work is entirely additive — no new dependencies, no changes to the core game loop, no new rendering infrastructure. Items are first-class ECS entities with a `Position` component while on the ground and no `Position` while carried. This single invariant ("position OR parent reference, never both") drives the entire architecture and eliminates the most common phantom-rendering and stale-reference bugs. The existing `EntityFactory`, `ResourceLoader`, `DeathSystem`, and event bus patterns are replicated directly for items, producing a system that is immediately familiar to anyone reading the existing codebase and testable in isolation at every step.

The recommended implementation order is bottom-up by dependency: components first, then the data pipeline (ItemRegistry + ItemFactory), then systems that produce items (LootSystem), then systems that consume them (PickupSystem, EquipmentSystem), and finally the inventory UI state. This order means every phase ships independently testable functionality before the next phase begins. The eight pitfalls identified in research are all addressable at their natural phase boundary — none require retrofitting if the correct design is adopted from the start.

The two highest-consequence risks are freeze/thaw inventory corruption and stat delta-mutation bugs. Freeze/thaw: inventory item entities must be excluded from the `MapContainer.freeze()` pass alongside the player entity, or they are silently destroyed during map transitions. Stat mutation: equipment bonuses must never be applied as deltas to `Stats` fields; a separate `EffectiveStats` component computed by `EquipmentSystem` each frame eliminates an entire class of irreversible state bugs. Both risks are binary — get them right at the foundation phase and they disappear entirely; discover them after shipping the equipment phase and recovery is a significant audit. Every other pitfall is recoverable at LOW to MEDIUM cost.

## Key Findings

### Recommended Stack

No new packages are required. The entire item system is implemented with the existing Python 3.13 stdlib (`dataclasses`, `enum`, `random.choices`, `typing`, `collections`), pygame 2.6.1 draw primitives, and esper 3.7 component queries. All APIs were verified live against the running environment — not inferred. Critical decisions: use `esper.try_component()` (not `try/except KeyError`) for all optional item component access; use `random.choices(pool, weights=weights, k=1)[0]` for loot rolls (C-level, 0.0013ms/call, no precomputation needed); use `panel.subsurface(rect)` with a logical `scroll_offset` integer for the inventory list (not `pygame.Surface.scroll()`).

**Core technologies:**
- Python 3.13 stdlib (`dataclasses`, `random.choices`, `enum`, `typing`): all new ECS components and loot logic — no third-party libraries needed or justified
- pygame 2.6.1 (`Surface`, `draw.rect`, `font`, `Rect.collidepoint`, `subsurface`): inventory modal UI rendered with the same primitives already used by `UISystem`
- esper 3.7 (`try_component`, `get_components`, `add_component`, `remove_component`, `dispatch_event`): item entity lifecycle and event routing — all APIs confirmed available and working

See STACK.md for full API verification table, all component dataclass definitions, the JSON pipeline format, and the complete "What NOT to Add" rationale (no `pygame_gui`, no `numpy`, no per-slot component classes, no custom weighted-random class).

### Expected Features

The minimum viable item loop is: monster dies → drops loot → player picks it up → equips or uses it → combat stats change. All eight table-stakes features are required for this loop to close; none can be deferred to v1.x without leaving the loop open or the system feeling broken.

**Must have (table stakes — closes the item loop):**
- Item ECS entity (templates + `ItemFactory`) — universal prerequisite; everything else depends on items existing as world entities
- Pick up (`g` key) — entry point to the loop; removes `Position`, appends entity ID to `Inventory.items`; weight-checked before accepting
- Weight / carry capacity — stated project design goal; blocks pickup when over limit with log feedback
- Loot drops from monsters — item source; `LootTable` component on monster templates + `LootSystem` listening to `"entity_died"`
- Inventory screen (`i` key, `GameStates.INVENTORY`) — players must be able to see and manage what they carry; arrow-key navigation, `d` drop, `Esc` close
- Equipment slots — gear needs a mechanical home; `Equipment` component with `Dict[str, Optional[int]]` slot map on the bearer entity
- Stat modification from equipment — equipment is cosmetic without this; `EffectiveStats` component computed by `EquipmentSystem` each frame
- Consumable items (heal) — simplest test of the consumable pipeline; health potion restores HP, item entity deleted on use

**Should have (add after v1 validation):**
- Material component + flavor descriptions — simulation feel; `ItemMaterial` component + `MaterialProperties` registry; `Description` updated to mention material type
- Equipment visual feedback in sidebar — extend `UISystem.draw_sidebar()` to show current loadout at a glance
- Additional consumable effects (mana restore, poison, teleport) — once the heal pipeline is confirmed working
- Identified/unidentified items — replayability via per-run `unknown_name` mapping; defer until consumables are stable

**Defer to v2+:**
- Material interaction rules (wood burns, metal conducts, glass shatters) — depends on fire/lightning/impact event systems not yet built
- Item crafting — independent milestone; do not scope here
- Item cursing / blessing — adds UI affordances and content design work beyond v1.4 scope

**Anti-features to reject explicitly:** nested containers (bags-in-bags), item stacking as a general feature, real-time drag-and-drop UI, item durability/repair. Each is documented in FEATURES.md with specific architectural or design rationale for rejection.

See FEATURES.md for full prioritization matrix, dependency graph, and system impact analysis.

### Architecture Approach

Items live as ECS entities in exactly one of three states: on ground (has `Position` + `Renderable`, no `Contained`), in inventory (no `Position`, has `Contained(owner, slot="pack")`), or equipped (no `Position`, has `Contained(owner, slot=<slot_name>)`). State transitions are performed by removing and adding components atomically. The `EquipmentSystem` runs before `CombatSystem` each frame to compute `EffectiveStats` from base `Stats` plus equipped item bonuses. The `LootSystem` registers a separate `"entity_died"` handler alongside `DeathSystem`'s existing handler, keeping loot spawning fully decoupled from corpse transformation. The `MapContainer.freeze()` call in `transition_map()` must receive a full entity closure (player + all items in `Inventory.items` + equipped items) to avoid silently destroying carried items during map transitions.

**Major components:**
1. `ItemRegistry` + `ItemFactory` (`entities/item_registry.py`, `entities/item_factory.py`) — data pipeline mirroring `EntityRegistry`/`EntityFactory`; `assets/data/items.json` parallel to `entities.json`
2. New ECS components (`ecs/components.py`): `Portable`, `Contained`, `Equippable`, `Consumable`, `ItemMaterial`, `EffectiveStats`, `LootTable`, `PickupRequest`, `EquipRequest`
3. Four new processor classes: `EquipmentSystem`, `PickupSystem`, `LootSystem`, `ItemActionSystem` — may be unified into fewer files for v1.4 scope
4. `GameStates.INVENTORY = 5` — new modal state in `config.py`; routes inventory key input; blocks turn advancement while open
5. Inventory UI (render call from `Game.draw()` when `current_state == INVENTORY`) — modal overlay over frozen game world; arrow-key navigation, `d` drop, `u`/Enter use/equip, Esc close

**Key architectural decisions with strong rationale:**
- Remove `Position` on pickup (not an `InInventory` tag) — prevents `RenderSystem`/`MovementSystem` from processing carried items with no change to those systems
- `EffectiveStats` component computed each frame (not delta mutation of `Stats`) — base stats never corrupted by equip/unequip cycle
- `LootSystem` as a separate event handler (not inline in `DeathSystem`) — single responsibility; independently testable
- Entity closure exclusion in `freeze()` computed by the caller, not by `MapContainer` — no inventory logic leaks into the map layer

The recommended build order is 9 steps from components through UI, each independently testable. See ARCHITECTURE.md for full data flow diagrams, code templates for all new systems, the complete modified/unchanged file inventory, and internal boundary documentation.

### Critical Pitfalls

1. **Freeze/thaw inventory corruption (entity ID staleness)** — `MapContainer.freeze()` deletes all entities not in the exclusion list; carried item entities have no `Position` and will be silently destroyed. Prevention: implement `get_entity_closure(player_entity)` returning player + all `Inventory.items` IDs + equipped item IDs; pass full list to `freeze()`. Must be wired before any test combining "player holds an item" with "player crosses a portal." Recovery cost is HIGH if discovered after the milestone ships.

2. **Stat delta mutation leads to irreversible state** — applying equipment bonuses as `stats.power += bonus` on equip causes double-apply on re-equip, undershoots on unequip after debuffs, and requires tracking prior values to unequip safely. Prevention: keep `Stats` as immutable base values; `EffectiveStats` component computed from scratch by `EquipmentSystem` each frame; `CombatSystem` reads `EffectiveStats`. Costs nothing to adopt upfront; MEDIUM recovery cost to retrofit.

3. **Phantom rendering of inventoried items** — if `Position` is updated (not removed) on pickup, the item glyph renders at the carrier's tile or at `(0,0)`. Prevention: enforce "Position OR parent reference, never both" with assertions in pickup and drop functions. Write the assertion as the first test.

4. **Orphaned item entities on NPC death** — `DeathSystem.on_entity_died()` currently strips AI/Stats/Blocker but has no `Inventory` handling; items in an NPC's inventory become invisible orphans with no position and no owner, accumulating silently. Prevention: extend `on_entity_died()` to drop or destroy all items in `Inventory.items` before removing the `Inventory` component from the dead entity.

5. **Loot drop stacking on death tile** — multiple items dropped at the exact same `(x, y)` are invisible to each other; only one renders and only one is reachable by pickup logic. Prevention: implement `find_drop_positions(x, y, layer, count)` that spreads items to adjacent walkable tiles; items that cannot be placed are destroyed with a log message.

Additional pitfalls (MEDIUM priority, addressed at natural phase boundaries): AI system processing item entities if JSON templates copy creature fields (prevent with `ItemFactory` assertion); inventory UI state conflict if opened during `ENEMY_TURN` (gate behind `is_player_turn()` guard or `INVENTORY` enum value); material interaction O(n²) cascade (per-turn accumulator, not recursive `dispatch_event`).

## Implications for Roadmap

A 4-phase structure is recommended. Feature dependencies drive the ordering; pitfall prevention drives what must be established within each phase before the next begins.

### Phase 1: Item Entity Foundation

**Rationale:** Item ECS entity is the universal prerequisite for every other feature. Nothing can be built or tested without items existing as world entities. The freeze/thaw protection (`get_entity_closure()`) must also be established here — before any portal-transit test — because discovery after the fact requires a HIGH-cost audit. All new component definitions live here too; downstream phases just use them.
**Delivers:** All new ECS component definitions in `ecs/components.py`; `ItemTemplate` + `ItemRegistry` + `ResourceLoader.load_items()`; `assets/data/items.json` with 3-5 initial items; `ItemFactory.create_on_ground()` and `create_in_inventory()`; `get_entity_closure()` wired into `transition_map()`; items visible on the map via existing `RenderSystem` (no changes to render pipeline).
**Addresses:** Item ECS entity (table stakes), Weight/carry capacity foundation (Item.weight field on Portable)
**Avoids:** Pitfall 1 (freeze/thaw established here), Pitfall 2 (Position-removal invariant enforced as assertion), Pitfall 4 (ItemFactory validates no AI/Blocker on item entities)
**Research flag:** Standard pattern — mirrors EntityFactory/EntityRegistry exactly; codebase already has `SpriteLayer.ITEMS = 3`. No additional research needed.

### Phase 2: Pickup, Loot Drops, and Inventory Screen

**Rationale:** Once items exist on the ground, the pickup mechanic and inventory display are the minimal complete UI loop. Loot drops can be built in parallel with the inventory screen because `LootSystem` depends only on `ItemFactory` (Phase 1), not on the inventory UI. Both ship together to deliver the first complete user-visible loop: monster drops loot → player picks it up → sees it in inventory. The `DeathSystem` extension for orphaned items and `find_drop_positions()` for scatter positioning are addressed here at their natural phase boundary.
**Delivers:** `g` key pickup with weight check and log feedback; `LootTable` on orc/wolf entities in `entities.json`; `LootSystem` listening to `"entity_died"`; `DeathSystem` extended to drop/destroy NPC inventory items on death; `find_drop_positions()` for scatter; `GameStates.INVENTORY = 5` in `config.py`; inventory modal with arrow-key navigation, item name + description display, drop action (`d`), close (`Esc`); inventory state guard blocking actions during `ENEMY_TURN`.
**Addresses:** Pick up, Weight/carry capacity, Loot drops, Inventory screen (all table stakes)
**Avoids:** Pitfall 3 (orphaned items on NPC death — DeathSystem extended here), Pitfall 6 (loot drop positioning — find_drop_positions implemented here), Pitfall 7 (inventory UI state conflict — guard established here)
**Research flag:** Standard pattern — `random.choices` loot rolls and pygame modal UI with confirmed APIs. No additional research needed.

### Phase 3: Equipment Slots and Combat Integration

**Rationale:** Equipment requires the inventory screen as its entry point (equip action initiated from inventory UI) and the item entity foundation. Stat modification must ship with equipment — gear is cosmetic without it. The `EquipmentSystem` + `EffectiveStats` + `CombatSystem` modification is a tightly coupled unit that must ship together. Run order constraint: `EquipmentSystem` registered before `CombatSystem` in `game_states.py`.
**Delivers:** `Equippable` component, `Equipment` component on player entity, equip/unequip actions from inventory UI, slot-collision swap (equipping to occupied slot moves displaced item back to inventory), `EquipmentSystem` processor computing `EffectiveStats` each frame, `CombatSystem` updated to read `EffectiveStats` via `_get_power()` / `_get_defense()` helper methods.
**Addresses:** Equipment slots, Stat modification from equipment (both table stakes)
**Avoids:** Pitfall 5 (stat delta mutation — `EffectiveStats` pattern adopted, not retrofitted)
**Research flag:** Standard ECS equipment pattern; `CombatSystem` integration is a localized change with confirmed API. No additional research needed.

### Phase 4: Consumables and v1.x Polish

**Rationale:** Consumables depend on the inventory screen (use action initiated there) and the item entity pipeline — both now complete. The health potion is the minimal test of the consumable dispatch pipeline; additional effects can be added incrementally once the pipeline is confirmed. Material component and equipment sidebar are low-complexity polish items appropriate for this phase.
**Delivers:** `Consumable` component, `"heal"` effect restoring HP, item entity deleted on use, log message; equipment loadout display in `UISystem.draw_sidebar()`; `ItemMaterial` component + `MaterialProperties` registry data; `Description` updated to mention material type for applicable items.
**Addresses:** Consumable items (table stakes), Material component + flavor descriptions, Equipment visual feedback in sidebar (both v1.x should-haves)
**Avoids:** Material interaction O(n²) cascade — material interaction *rules* (burns/conducts/shatters) explicitly deferred; only the data (`ItemMaterial` component) is added here
**Research flag:** Consumable effect dispatch follows existing `log_message` event pattern exactly. No additional research needed.

### Phase Ordering Rationale

- **Foundation before features:** Item ECS entity is a universal prerequisite; it ships first in isolation. This is non-negotiable — every feature in every downstream phase requires items to exist as world entities.
- **Loot and pickup together in Phase 2:** Loot drops produce floor items; the inventory screen consumes them. Building both in the same phase delivers the first complete user-visible loop rather than two half-loops that independently pass tests but produce no observable gameplay.
- **Equipment after inventory UI:** The equip action has no entry point without the inventory screen. Building equipment before Phase 2 produces code that can only be tested programmatically and requires the inventory UI to be retrofitted around it.
- **Consumables last:** They depend on everything above them but add no new infrastructure; they are the cleanest final phase with the smallest blast radius.
- **Pitfall prevention is phase-zero work within each phase:** `get_entity_closure()`, the `Position`-removal invariant, `ItemFactory` validation assertions, the `DeathSystem` inventory cleanup, and the `EffectiveStats` pattern are all zero-extra-cost if adopted at their natural phase boundary. The pitfall research is the primary driver of what must be in each phase.

### Research Flags

Phases with standard patterns (skip `/gsd:research-phase` — all confirmed):
- **Phase 1 (Item Entity Foundation):** Mirrors existing EntityFactory/EntityRegistry pattern exactly; `SpriteLayer.ITEMS = 3` already defined; all component APIs verified live.
- **Phase 2 (Pickup, Loot, Inventory Screen):** `random.choices` loot rolls and pygame modal UI both confirmed against running environment. `DeathSystem` event pattern read directly from source.
- **Phase 3 (Equipment + Combat):** `EffectiveStats` pattern is a well-documented ECS convention; `CombatSystem` integration is a localized change to two methods.
- **Phase 4 (Consumables + Polish):** Consumable effect dispatch follows existing `log_message` event pattern; `UISystem.draw_sidebar()` extension is additive.

No phases require `/gsd:research-phase` — all patterns are either confirmed in the existing codebase or verified live against the running stack.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All APIs verified live against Python 3.13.11, pygame 2.6.1, esper 3.7; performance benchmarked (`random.choices` 0.0013ms/call); no inference |
| Features | HIGH | Table stakes derived from codebase integration points and rogue-like genre canon; project spec explicitly names weight-based capacity and contextual loot; dependency graph validated against source |
| Architecture | HIGH | Direct codebase analysis of all integration points; `freeze()`/`thaw()` contract read from `map_container.py` source; event pattern confirmed from `death_system.py`; no inferences — all verified from source |
| Pitfalls | HIGH | All 8 pitfalls grounded in specific codebase line references; 2 (freeze/thaw, stat mutation) documented as established project decisions in `.planning/PROJECT.md` v1.2 |

**Overall confidence:** HIGH

### Gaps to Address

- **NPC inventory handling during freeze/thaw:** The architecture defers NPC inventories to a future extension. The `get_entity_closure()` helper is written to support recursive containers but only the player entity closure is wired in v1.4. Flag explicitly in the phase plan: no NPC template may include an `Inventory` component until NPC inventory freeze/thaw ID remapping is implemented.

- **`Stats` base field placement:** PITFALLS.md recommends adding explicit `base_power` / `base_defense` fields to `Stats`. ARCHITECTURE.md's `EffectiveStats` approach reads the existing `stats.power` as the base without adding fields. The two approaches are compatible but differ in field location. The roadmap phase plan should pick one explicitly and document it — this is a one-line decision but affects every reference to base stats in combat tests.

- **Multi-item pickup at same tile:** The pickup flow handles one item per `g` keypress. When loot scatter places multiple items on adjacent tiles, the player picks them up one at a time. A "pick up all" (`G`) action is not in v1.4 scope but will be the first UX request after loot drops ship. Note for v1.x backlog.

## Sources

### Primary (HIGH confidence — live codebase analysis)
- `ecs/components.py` — existing `Stats`, `Inventory`, `Name`, `Action` component shapes; `Inventory.items: List` stub (line 52)
- `entities/entity_factory.py` — conditional component attachment pattern
- `entities/entity_registry.py` — `EntityTemplate` flyweight pattern
- `services/resource_loader.py` — JSON validation + registry population pattern
- `config.py` — `SpriteLayer.ITEMS = 3` (line 37), `GameStates` enum
- `ecs/systems/ui_system.py` — `pygame.font.SysFont`, `pygame.draw.rect` pattern
- `ecs/systems/combat_system.py` — `Stats` usage, `AttackIntent` pattern, direct `stats.power` read (line 14)
- `ecs/systems/death_system.py` — `on_entity_died` handler, `esper.set_handler` event pattern (lines 11-47)
- `map/map_container.py` — `freeze()`/`thaw()` contract, `exclude_entities` parameter (lines 64-92)
- `game_states.py` — `GameStates` enum, `transition_map()`, `TARGETING` state routing
- `services/party_service.py` — `Inventory()` component already on player; `Action(name="Items")` already in `ActionList`
- `.planning/PROJECT.md` v1.2 decisions — "Coordinates-only AI state: Never entity IDs; freeze/thaw assigns new IDs breaking references"
- `.planning/PROJECT.md` v1.4 constraints — "Items are entities — position OR parent reference, never both"
- Codebase version: post-v1.3, commit `68bfec9`

### Primary (HIGH confidence — live API verification)
- Python 3.13.11: `random.choices` 0.0013ms/call at 10K iterations; `dataclasses`, `enum` confirmed
- pygame 2.6.1: `Surface.subsurface`, `Rect.collidepoint`, `font.get_linesize()` returns 16px at size 14; all confirmed
- esper 3.7: `try_component` returns `None` on missing (not `KeyError`); `get_components`, `delete_entity`, `dispatch_event`, `add_component`, `remove_component` all confirmed

### Secondary (HIGH confidence — established genre conventions)
- Rogue-like inventory conventions: NetHack, DCSS, Brogue — pick-up/drop/equip/use as table stakes; weight-based capacity; keyboard-driven modal inventory; identified/unidentified items as differentiator
- ECS item-as-entity pattern: items as entities rather than abstract data structures is the standard ECS approach — confirmed directly in existing codebase architecture and documentation

---
*Research completed: 2026-02-15*
*Ready for roadmap: yes*
