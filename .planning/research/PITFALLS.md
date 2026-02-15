# Pitfalls Research

**Domain:** Item & Inventory system added to existing esper ECS rogue-like
**Researched:** 2026-02-15
**Confidence:** HIGH — derived from direct codebase analysis of `map_container.py` (freeze/thaw),
`ecs/systems/render_system.py`, `ecs/systems/ai_system.py`, `ecs/systems/death_system.py`,
`ecs/systems/combat_system.py`, `entities/entity_factory.py`, `ecs/components.py`, and the
v1.2 decision log in `.planning/PROJECT.md`

---

## Critical Pitfalls

### Pitfall 1: Freeze/Thaw Destroys Inventory Item References (Entity ID Staleness)

**What goes wrong:**
`MapContainer.thaw()` calls `world.create_entity()` for every frozen entity, assigning brand-new
integer IDs. If `Inventory.items` stores entity IDs as bare integers, every ID in every inventory
is stale after a map transition. An NPC that survived freeze/thaw will hold IDs pointing to dead
or recycled entities. `esper.component_for_entity(stale_id, ...)` raises `KeyError` or, worse,
silently returns the wrong entity's component if that ID was recycled.

**Why it happens:**
The existing `Inventory` component (`ecs/components.py` line 52) is `items: List` with no
enforced type — the natural first implementation stores `int` entity IDs. The freeze/thaw
contract in `map_container.py` lines 86-92 gives no ID-preservation guarantee: `thaw()` calls
`world.create_entity()` and re-attaches component objects; the integer IDs are reassigned by
esper's internal counter. This is an established codebase decision: "Coordinates-only AI state:
Never entity IDs; freeze/thaw assigns new IDs breaking references" (PROJECT.md, v1.2 decisions).
Item inventories are the first place that design principle must be applied to data structures
other than AI state.

**How to avoid:**
Inventoried item entities must be excluded from the freeze pass together with their carrier.
Implement a `get_entity_closure(entity_id)` helper that returns the entity plus all IDs in its
`Inventory.items` and `Equipment` slots (recursively, for nested containers — not needed in v1.4
but the helper should be written to support it). Pass the full closure to `freeze()`:

```python
# In transition_map() in game_states.py, replace:
self.map_container.freeze(self.world, exclude_entities=[self.player_entity])

# With:
exclude = get_entity_closure(self.player_entity)
self.map_container.freeze(self.world, exclude_entities=exclude)
```

Never store bare entity IDs in `Inventory.items`. If a cross-reference must be stored (e.g.,
"this item is equipped by entity X"), store it in a component on the item itself
(`InInventory(owner: int)` written at pickup time) so that the component survives freeze as
object state — not as an ID cached in the carrier's list.

**Warning signs:**
- Inventory panel shows items but equipping/using raises `KeyError`
- Items silently disappear from player inventory after the first map transition
- NPC with loot drops nothing on death because its `Inventory.items` list holds stale IDs

**Phase to address:** The phase that establishes the item entity foundation and pickup/drop.
`get_entity_closure()` must exist and be wired into `transition_map()` before any test that
combines "player holds an item" with "player crosses a portal."

---

### Pitfall 2: RenderSystem Renders Inventoried Items at Phantom Positions

**What goes wrong:**
`RenderSystem.process()` queries `esper.get_components(Position, Renderable)`. Items on the ground
legitimately have `Position`. If a picked-up item's `Position` component is merely updated to the
carrier's coordinates (rather than removed), the item glyph renders on the map at the carrier's
tile — stacking with the carrier's own glyph. If `Position` is simply never removed and never
updated, the item renders at (0,0) or wherever it last rested.

**Why it happens:**
Updating position feels easier than removing and re-adding a component. The `Position` component
already exists; changing `pos.x, pos.y` is one line. The rendering consequence — a phantom glyph
— only appears at runtime and may be missed if testing focuses on inventory logic rather than the
map display.

**How to avoid:**
Use `Position` as the binary "on map" flag. The architectural constraint from PROJECT.md is
explicit: "Items are entities — position OR parent reference, never both."

```python
# Pickup: remove Position, add InInventory
esper.remove_component(item_ent, Position)
esper.add_component(item_ent, InInventory(owner=carrier_ent))

# Drop: remove InInventory, add Position at drop location
esper.remove_component(item_ent, InInventory)
esper.add_component(item_ent, Position(drop_x, drop_y, drop_layer))
```

Write the assertion as the first test: after pickup, assert
`esper.has_component(item_ent, Position)` is `False`. After drop, assert it is `True`.

**Warning signs:**
- Item glyph visible at (0,0) after pickup
- Two glyphs appear at the same tile when a character carrying an item stands on it
- Item glyph remains at its original tile after being picked up

**Phase to address:** Item pickup/drop phase — the `Position`-as-flag invariant is the first
invariant enforced before any other item logic is built on top of it.

---

### Pitfall 3: DeathSystem Leaves Orphaned Inventory Item Entities

**What goes wrong:**
`DeathSystem.on_entity_died()` strips AI, Stats, Blocker, and related components and converts
the entity to a corpse (death_system.py lines 29-43). It does NOT touch `Inventory` or any item
entities referenced by it. Item entities in a dead NPC's inventory survive in the ECS world
with no `Position` and no owner reference. They are invisible (RenderSystem skips them — no
`Position`), cannot be picked up (no map position), and accumulate silently across many combat
sessions.

**Why it happens:**
DeathSystem operates on the dying entity itself. Item cleanup requires reaching out to a
different set of entities (the items), which is a second concern the current system has no reason
to know about. The entity leak is silent — no crash, no visible artifact — so it survives testing.

**How to avoid:**
Extend `DeathSystem.on_entity_died()` with an inventory drop pass. When `Inventory` is present
on the dead entity, iterate `inv.items`, call `find_drop_position()` for each, and assign
`Position` to each item entity before removing `Inventory` from the corpse:

```python
# In on_entity_died, before removing Inventory:
if esper.has_component(entity, Inventory):
    inv = esper.component_for_entity(entity, Inventory)
    try:
        death_pos = esper.component_for_entity(entity, Position)
        for item_ent in list(inv.items):
            drop_pos = find_drop_position(death_pos.x, death_pos.y, death_pos.layer)
            if drop_pos:
                esper.add_component(item_ent, Position(drop_pos.x, drop_pos.y, drop_pos.layer))
            else:
                esper.delete_entity(item_ent, immediate=True)
    except KeyError:
        pass
    esper.remove_component(entity, Inventory)
```

**Warning signs:**
- ECS entity count grows unboundedly during extended play (`len(esper._world._entities)`)
- NPCs that visually had items (pre-death investigation showed them) drop nothing
- Memory consumption increases proportionally to combat session length

**Phase to address:** The loot drop / DeathSystem extension phase. Must be addressed before
any NPC template includes an `Inventory` component. A diagnostic test: spawn an NPC with
inventory, kill it, assert `esper.entity_exists(item_ent)` and the item has `Position`.

---

### Pitfall 4: AI System Processing Item Entities as Actors

**What goes wrong:**
`AISystem.process()` queries `esper.get_components(AI, AIBehaviorState, Position)`. Items will
not naturally have `AI` components — but if an item JSON template is copy-pasted from a creature
template without resetting the `"ai"` field, `EntityFactory.create()` will add `AI` and
`AIBehaviorState` to the item. The AI system will then route a sword through wander/chase logic.

A subtler issue: `AISystem._get_blocker_at()` scans all `(Position, Blocker)` entities to
check tile occupancy. Items on the ground that accidentally carry `Blocker` will block NPC
movement. This is not a crash — it silently makes dropped items impassable obstacles.

**Why it happens:**
The JSON entity template pipeline has no type distinction between "creature" and "item" templates.
`EntityFactory.create()` attaches `AI` whenever `template.ai` is truthy. A copied-and-edited
JSON template is the most likely source of the error.

**How to avoid:**
- Add an `"entity_type"` field to item templates with value `"item"`. Validate in
  `EntityFactory` (or a dedicated `ItemFactory`) that item-type templates produce no `AI` or
  `Blocker` components. Raise `ValueError` if they do.
- Items on the ground must never have `Blocker`. Enforce this as a post-creation assertion in
  `ItemFactory.create()`.

**Warning signs:**
- AI system log messages reference item names
- Dropped item prevents NPC movement through its tile
- AI system performance degrades proportionally to item count on the ground

**Phase to address:** Item template and factory phase. The validation should be an assertion in
`ItemFactory.create()` that fires at entity creation time, not discovered later in gameplay.

---

### Pitfall 5: Stat Recalculation Bugs — Delta Mutation Leads to Irreversible State

**What goes wrong:**
The existing `Stats` component stores `power` and `defense` as plain integers. The natural
equipment implementation applies a bonus as a delta: `stats.power += weapon.bonus_power` on equip,
`stats.power -= weapon.bonus_power` on unequip. This produces three failure modes:

1. **Double-apply**: Equipping a weapon that is already in the equipped slot adds the bonus
   twice. The UI may not prevent this if the equip slot check is missed.
2. **Unequip undershoots**: If the entity took a stat-lowering effect between equip and unequip,
   the stored bonus is subtracted from an already-reduced value, pushing stats below base.
3. **Corpse stat inflation**: DeathSystem removes `Stats` (`death_system.py` line 29) — so delta
   mutation on a live entity is harmless post-death. But if any system reads stats from a corpse
   before `on_entity_died` fires (e.g., a "corpse inspection" feature), it may read inflated
   values from equipment that was never subtracted.

**Why it happens:**
Delta mutation of a mutable dataclass field is the simplest implementation. There is no type
system enforcement preventing it. The failure modes only appear at runtime in specific sequences
(equip → debuff → unequip), which unit tests may not cover.

**How to avoid:**
Adopt a "base + recalculate" model before writing any equip logic. Add base fields to `Stats`:

```python
@dataclass
class Stats:
    # Base values set from template — never modified by equipment
    base_power: int
    base_defense: int
    # Effective values — recalculated from base + equipment on every equip/unequip
    power: int
    defense: int
    # hp, mana etc remain mutable (they take damage)
    hp: int
    max_hp: int
    ...
```

Write a `recalculate_stats(entity)` function that reads an `Equipment` component and writes
effective values from scratch:

```python
def recalculate_stats(entity):
    stats = esper.component_for_entity(entity, Stats)
    bonus_power = 0
    bonus_defense = 0
    if esper.has_component(entity, Equipment):
        equip = esper.component_for_entity(entity, Equipment)
        for slot_item in equip.equipped.values():
            if slot_item and esper.has_component(slot_item, ItemStats):
                item_stats = esper.component_for_entity(slot_item, ItemStats)
                bonus_power += item_stats.bonus_power
                bonus_defense += item_stats.bonus_defense
    stats.power = stats.base_power + bonus_power
    stats.defense = stats.base_defense + bonus_defense
```

Call `recalculate_stats()` only on equip and unequip events — not every frame. All other systems
(`CombatSystem`, AI perception checks) continue reading `stats.power` and `stats.defense` as
before. No change required in `CombatSystem`.

**Warning signs:**
- Unequipping an item results in lower stats than the pre-equip baseline
- Stats grow with each equip/unequip cycle on the same item
- UI shows correct base stats, but combat damage calculations use different values

**Phase to address:** Equipment slot phase. The `base_power` / `base_defense` split and
`recalculate_stats()` function must be written before any equip logic — never retrofitted.

---

### Pitfall 6: Loot Drop Positioning on Occupied or Walled Death Tiles

**What goes wrong:**
When a monster dies adjacent to a wall or in a narrow corridor, multiple loot items spawned at
the exact death tile occupy the same position. `RenderSystem` renders only the highest
sprite-layer item; the others are invisible. Pickup logic that returns "the first item at (x,y)"
returns only one — the rest are permanently unreachable until the player moves to an adjacent tile
where nothing was dropped.

**Why it happens:**
Loot drop code that does `Position(death_pos.x, death_pos.y)` for every item in the loot list
is correct in intent but incorrect in spatial reasoning. Multiple entities at the same tile are
not errors in the current ECS — the system has no uniqueness constraint on positions. The
rendering and pickup bugs are the only symptoms.

**How to avoid:**
Implement a `find_drop_positions(x, y, layer, count)` function that returns a list of distinct
walkable tile positions starting from (x,y), then spreading to adjacent tiles:

```python
def find_drop_positions(x, y, layer, count, map_container):
    candidates = [(x, y)]
    for dx, dy in [(0,1),(1,0),(0,-1),(-1,0),(1,1),(-1,1),(1,-1),(-1,-1)]:
        candidates.append((x+dx, y+dy))
    positions = []
    for cx, cy in candidates:
        tile = map_container.get_tile(cx, cy, layer)
        if tile and tile.walkable and len(positions) < count:
            positions.append((cx, cy))
    return positions  # may be shorter than count if not enough walkable tiles
```

Items that cannot be placed because no walkable tile is found within the scatter radius should
be destroyed with a log message rather than silently placed on an impassable tile or stacked.

Pickup logic must always return ALL items at a position, not just the first one. Use a
list-returning function: `get_items_at(x, y, layer) -> List[int]`.

**Warning signs:**
- Killing a monster that drops 3+ items leaves only 1 item visible
- Item count in world does not match expected loot over many combats
- Player can stand on a tile and "pick up" the same item multiple times (recycled IDs)

**Phase to address:** Loot drop / DeathSystem extension phase. A dedicated test: kill a monster
with a 4-item loot table in a corner; assert 4 items exist in the world with distinct `Position`
components, all on walkable tiles.

---

### Pitfall 7: Inventory UI State Conflict with Game State Machine

**What goes wrong:**
The current state machine uses `GameStates.TARGETING` to block normal input during targeting.
There is no `INVENTORY` state. If the inventory screen is opened by key press without adding a
guard on `turn_system.current_state`, the player can interact with their inventory during
`ENEMY_TURN` — equipping a sword while enemies are acting. The game won't crash, but item state
mutations (equipping, consuming, dropping) fire at an unexpected point in the turn cycle. Stat
recalculations triggered mid-enemy-turn affect enemies' current-turn combat if they act after
the player's inventory interaction.

**Why it happens:**
Adding an inventory overlay feels like a UI concern, not a game-state concern. The instinct is
to handle it with a flag on the `Game` state (`self.inventory_open = True`) rather than
extending `GameStates`. But `Game.handle_player_input()` only guards movement input — it does
not gate item actions behind turn state.

**How to avoid:**
Add `INVENTORY` to the `GameStates` enum in `config.py`. Treat opening inventory the same as
entering targeting: `turn_system.set_state(GameStates.INVENTORY)`. Block all enemy AI
processing while in `INVENTORY` state (the guard in `AISystem.process()` already checks
`turn_system.current_state != GameStates.ENEMY_TURN`; add `INVENTORY` handling there or treat
it as still being `PLAYER_TURN` depending on design intent).

An acceptable alternative for v1.4 scope: allow inventory during player turn only by checking
`turn_system.is_player_turn()` before processing any inventory key input — simpler, no new
enum value needed. But document this as a known limitation.

**Warning signs:**
- Consuming a healing potion during enemy turn immediately before an enemy attack negates the
  hit (HP was restored mid-turn-cycle)
- Dropping a weapon while an enemy is attacking causes a `KeyError` if the weapon's entity ID
  was referenced in the enemy's AttackIntent
- Inventory interactions produce log messages out of turn sequence order

**Phase to address:** Inventory UI phase. The state guard must be designed before any key
binding for inventory actions is implemented. Decide: new `INVENTORY` state OR `is_player_turn()`
guard — document the choice explicitly.

---

### Pitfall 8: Material Interaction Cascades Create O(n²) Event Storms

**What goes wrong:**
Material interactions (fire spreads to wooden items, metal items conduct electricity to adjacent
metal items, glass shatters on impact) are event-driven. If the event handler for "item_ignited"
checks every item in the world for adjacency and fires another "item_ignited" event for each
neighboring wooden item, a single fire source triggers a cascade. With 10 wooden items in a
room, event 1 triggers 9 more events, each of which triggers up to 8 more — exponential growth
bounded only by the world item count.

**Why it happens:**
Material interaction is designed event-by-event rather than as a spatial propagation step.
`esper.dispatch_event()` is synchronous (fires the handler immediately in esper 3.x — confirmed
by the existing usage pattern). Each event dispatches more events before the first handler
returns.

**How to avoid:**
Do not fire material interaction events recursively within handlers. Instead, collect affected
items into a "pending interactions" set during each turn's material processing step, then resolve
the set once:

```python
# Per-turn material resolution — called once at end of PLAYER_TURN or ENEMY_TURN
def resolve_material_interactions(pending_ignitions):
    newly_ignited = set()
    for item_ent in pending_ignitions:
        if not esper.has_component(item_ent, Position):
            continue  # in inventory — not a ground interaction
        pos = esper.component_for_entity(item_ent, Position)
        for neighbor in get_items_at_adjacent_tiles(pos.x, pos.y, pos.layer):
            mat = esper.component_for_entity(neighbor, Material)
            if mat.type == "wood" and neighbor not in newly_ignited:
                newly_ignited.add(neighbor)
    # Apply newly_ignited in a second pass — no recursive dispatch
    for item_ent in newly_ignited:
        apply_burn_effect(item_ent)
```

Limit cascade depth explicitly: fire spreads at most 1 tile per turn. This is both
simulation-correct and O(n) per turn.

**Warning signs:**
- Game freezes for several seconds when a fire source appears near multiple wooden items
- Stack overflow or recursion depth error in the message log
- Turn processing time spikes from <1 ms to >100 ms when items are burning

**Phase to address:** Material interaction phase (not the initial item foundation phase — this
pitfall only matters once material types and interaction rules are introduced). Flag the phase
plan: "fire material-interaction event processing via per-turn accumulator, not recursive
dispatch."

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store item entity IDs as bare `int` in `Inventory.items` | Simple list append | All IDs stale after freeze/thaw; silent `KeyError` on every map transition with carried items | Never — use entity closure exclusion from day one |
| Apply equipment bonuses as deltas to `Stats.power`/`Stats.defense` | One-line equip implementation | Unequip undershoots, double-apply, no audit trail; requires full audit to fix | Never — base/effective split costs nothing up front |
| Keep `Position(0,0)` on inventoried items | Avoids remove/re-add component churn | Phantom glyph rendered at (0,0) every frame; RenderSystem processes item on every pass | Never — remove `Position` on pickup; re-add on drop |
| Skip `Inventory` cleanup in `DeathSystem` until NPC inventories exist | Faster first iteration | Silent entity leak accumulates; requires audit pass to find orphaned entities later | Only if the first phase guarantees no NPC carries `Inventory` — must fix before that changes |
| Global constant weight limit for all carriers | Simple capacity validation | All characters identical capacity; no differentiation; hard to retrofit per-entity capacity later | Acceptable as an initial validation test only; replace with per-entity field before any UI shows capacity |
| Process material interactions with recursive `dispatch_event` | Simplest event-driven model | Exponential cascade for adjacent materials; O(n²) freeze | Acceptable only if no more than 1 material interaction event can chain (e.g., glass shatters once, does not cascade) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| freeze/thaw + player inventory | `freeze(exclude_entities=[player_entity])` only; item entities freeze with the map and are destroyed | Compute full entity closure (player + all items in `Inventory.items` + `Equipment` slots) and exclude all from freeze |
| RenderSystem + inventoried items | Item retains `Position` when picked up; rendered on map every frame | Remove `Position` component entirely on pickup; re-add on drop |
| DeathSystem + NPC inventory | `on_entity_died` strips AI/Stats/Blocker but ignores `Inventory`; items become orphans | Extend `on_entity_died` to drop or destroy all inventoried items before removing `Inventory` component |
| AISystem + items on ground | `_get_blocker_at` scans `(Position, Blocker)`; items with `Blocker` block NPC pathfinding | Items must never have `Blocker`; enforce in `ItemFactory.create()` with assertion |
| Targeting system + item entities | `Targeting.potential_targets` (List of entity IDs) includes all entities in range; items in range become targettable | Filter `potential_targets` to only entities with `Stats` or an explicit `Targetable` tag component |
| CombatSystem + equipped weapons | `CombatSystem` reads `stats.power` directly (combat_system.py line 14); weapon bonuses must be already applied in `Stats.power` | `recalculate_stats()` called on equip/unequip; `CombatSystem` reads effective value with no changes required |
| JSON templates + item types | Copy-pasting creature template JSON with `"ai": true` or `"blocker": true` makes items behave as creatures | Add `"entity_type": "item"` field; `ItemFactory` asserts `ai=False, blocker=False` at creation time |
| Inventory UI + game state machine | Opening inventory during `ENEMY_TURN` allows mid-enemy-turn item actions | Gate inventory key input behind `turn_system.is_player_turn()` or add `INVENTORY` to `GameStates` |
| Material interactions + `dispatch_event` | Recursive event dispatch creates exponential cascade | Collect affected items in a set per turn; resolve set in a single pass at turn end |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| `_get_blocker_at` linear scan over all `(Position, Blocker)` entities | AI turn gets slower as on-ground item count grows | Items never have `Blocker`; the scan stays bounded to actual creature blockers | Noticeable with 50+ items on ground and 10+ active NPCs |
| `recalculate_stats()` called every frame instead of on equip/unequip events | Stats recalculation runs 60×/second for every entity with equipment | Call `recalculate_stats()` only from equip/unequip event handlers; stats are stable between those events | Immediately wasteful; noticeable with party of 3 + 20 equipped NPCs |
| `esper.get_components(Position, Renderable)` grows with loot scatter | Render pass processes every on-ground item; frame time grows with item density | Camera bounds culling already present; no action needed until 500+ on-ground items | Not a v1.4 concern at typical loot density |
| Synchronous recursive material cascade | Turn processing freezes with multiple adjacent flammable items | Per-turn accumulator pattern; max 1 tile spread per turn | Any room with 3+ adjacent wooden items near a fire source |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Weight overflow silently rejected | Player presses pickup key; nothing happens; no feedback | Dispatch `log_message` event: "[color=red]Too heavy to carry.[/color]" on weight overflow |
| Equipping an item to an occupied slot silently fails | Player selects new sword; old sword stays; new sword disappears | Auto-unequip old item to inventory on slot conflict; log the swap: "[color=yellow]Swapped [old] for [new].[/color]" |
| Inventory UI opened during targeting mode | State conflict: cursor interacts with inventory items | Block inventory open when `turn_system.current_state == GameStates.TARGETING` |
| Drop with no adjacent walkable tile silently destroys item | Rare item disappears near walls | Log "[color=orange]No room to drop item here.[/color]"; do not destroy silently unless explicitly documented |
| Consumable used from inventory without confirmation | Single keypress destroys a rare potion | Require ENTER after selecting a consumable; or provide "used X" log with clear feedback |

---

## "Looks Done But Isn't" Checklist

- [ ] **Pickup removes Position:** After pickup, `esper.has_component(item_ent, Position)` returns `False` and no glyph appears at the old tile
- [ ] **Drop restores Position:** After drop, `esper.has_component(item_ent, Position)` returns `True` at a walkable tile
- [ ] **Map transition with inventory:** Player picks up item, crosses portal, returns — inventory item count unchanged and all items usable
- [ ] **NPC death with inventory:** Kill an NPC with items — no orphaned entities (world entity count delta equals expected drops); all dropped items have `Position` on walkable tiles
- [ ] **Equip round-trip:** Equip item → verify `stats.power` increased; unequip → verify `stats.power` == original base value (not lower)
- [ ] **Double-equip guard:** Equip same item to same slot twice — item count in inventory unchanged; stats unchanged; no error
- [ ] **Loot in corner:** Kill monster with 4-item loot table against a wall — 4 distinct items on map at reachable tiles
- [ ] **Render isolation:** Pick up item → no phantom glyph on map; drop item → glyph at correct position, not at (0,0)
- [ ] **AI ignores items:** Items on ground — NPC wander/chase is not blocked; AI system does not route item entities through `_dispatch()`
- [ ] **Weight capacity feedback:** Attempt pickup over weight limit — receives log message, item stays on ground
- [ ] **Inventory state guard:** Attempting inventory action during `ENEMY_TURN` — blocked or no item state mutation occurs mid-turn

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Freeze/thaw ID staleness discovered after item milestone shipped | HIGH | Audit all `Inventory.items` and `Equipment` slot stores for bare int IDs; implement `get_entity_closure()`; wire into `transition_map()`; add test covering portal transit with carried item |
| Delta-mutation stat bugs discovered after equipment system shipped | MEDIUM | Add `base_power`, `base_defense` fields to `Stats`; write migration that sets base = current − sum(equipped bonuses); replace all delta writes with `recalculate_stats()` calls; run round-trip test |
| Orphaned item entities accumulate silently | LOW | Add diagnostic: track entity count before/after each `on_entity_died` call; write a cleanup scan for entities with no `Position` and no `InInventory` component; extend `DeathSystem` |
| Phantom item rendering bugs | LOW | Add `assert not esper.has_component(item, Position)` in `pickup_item()`; add `assert esper.has_component(item, Position)` in `drop_item()`; fix the component lifecycle |
| Material cascade freeze | LOW-MEDIUM | Replace recursive `dispatch_event` with per-turn accumulator pattern; cap spread at 1 tile per turn; profile to confirm O(n) |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Freeze/thaw ID staleness (Pitfall 1) | Item Entity Foundation — first phase; `get_entity_closure()` before any portal-transit test | Test: pick up item → cross portal → return → use item (no `KeyError`) |
| Phantom rendering of inventoried items (Pitfall 2) | Item pickup/drop | Test: `assert not esper.has_component(item, Position)` immediately after pickup |
| Orphaned item entities on death (Pitfall 3) | Loot drop / DeathSystem extension | Test: kill NPC with inventory → `esper.entity_exists(item)` True → item has `Position` on walkable tile |
| AI processing item entities (Pitfall 4) | Item template pipeline | Validation: `ItemFactory.create()` asserts no `AI` component produced; `assert not esper.has_component(item, AI)` |
| Stat recalculation bugs (Pitfall 5) | Equipment slots | Test: equip → unequip → assert `stats.power == stats.base_power`; property-based test for all combinations |
| Loot drop positioning (Pitfall 6) | Loot drop / DeathSystem extension | Test: kill monster with 4-item loot in a corner → 4 items on distinct walkable tiles |
| Inventory UI state conflict (Pitfall 7) | Inventory UI | Test: simulate inventory key input during `ENEMY_TURN` → no item state mutation; turn cycle unaffected |
| Material cascade (Pitfall 8) | Material interactions phase | Profiling test: place 10 adjacent wooden items near fire source → turn resolves in <5 ms |

---

## Sources

- `map/map_container.py` lines 64-92: freeze/thaw implementation (entity deletion, create_entity, ID reassignment)
- `ecs/components.py` lines 52-53: `Inventory` component definition (`items: List` — no type enforcement)
- `ecs/systems/render_system.py` lines 26-66: RenderSystem queries `(Position, Renderable)` for all entities
- `ecs/systems/ai_system.py` lines 49-58: AISystem filters `(AI, AIBehaviorState, Position)`; `_get_blocker_at` scans `(Position, Blocker)`
- `ecs/systems/death_system.py` lines 11-47: `on_entity_died` strips components, no inventory handling
- `ecs/systems/combat_system.py` lines 14: reads `stats.power` directly (no indirection layer)
- `entities/entity_factory.py`: conditional component attachment from template fields; no entity-type validation
- `.planning/PROJECT.md` — v1.2 decisions: "Coordinates-only AI state: Never entity IDs; freeze/thaw assigns new IDs breaking references"
- `.planning/PROJECT.md` — v1.4 constraints: "Items are entities — position OR parent reference, never both"
- Codebase version: post-v1.3, commit `68bfec9`

---
*Pitfalls research for: Item & Inventory System — simulation-first items as ECS entities in esper rogue-like*
*Researched: 2026-02-15*
