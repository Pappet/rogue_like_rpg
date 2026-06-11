# ROADMAP — From Roguelike to Living-World Simulation

> Source of truth for the project direction after v1.6. The history that led
> here lives in `DEV_JOURNAL.md`. Architecture rules live in `CLAUDE.md`.

## 1. Vision

A living, independent world the player travels through — not a dungeon the
player conquers. Villages and towns exist for their own sake: inhabitants
work, trade, sleep, gossip and have problems whether the player is present
or not. The player journeys between settlements, takes on quests for the
population, trades along price differences, and uncovers secrets the world
only hints at. Tone target: "Skyrim, but smaller and more alive — the world
does not wait for the player."

### Design Pillars

1. **The world is not player-centric.** NPCs act from their own needs and
   schedules. Quests grow out of the simulation state, not the other way
   around.
2. **Two-level simulation.** The active map is simulated in full ECS detail.
   Every other place is simulated *abstractly* (cheap, schedule/aggregate
   based) and reconciled when the player arrives. Nothing is allowed to be
   "frozen in time" from the player's point of view.
3. **Everything stays data-driven.** New settlements, NPCs, goods, quests
   and rumors are JSON content first, code second (CLAUDE.md Recipe A).
4. **Every phase ends playable.** Each phase below is a vertical slice with
   a visible in-game result — no multi-phase infrastructure detours.

## 2. What we already have (the foundation this builds on)

| Building block | Status | Reused for |
|---|---|---|
| World clock, day/night, 1 tick per turn | done | global simulation time |
| NPC schedules (`schedules.json`, target_meta "home") | done | abstract off-screen activity |
| AI states (WORK/SLEEP/SOCIALIZE/PATROL/CHASE...) | done | needs-driven behavior |
| Multi-map + portals + freeze/thaw, `travel_ticks` | done | settlements & travel time |
| Data-driven scenarios (`scenarios/village.json`) | done | more settlements |
| Items/equipment/consumables, loot, bump-dialogue | done | trade & quest rewards |
| `WorldMapState` (currently: minimap of active map) | stub | overworld travel screen |

## 3. Phases

### Phase A — World Skeleton: Places, Travel, Saving ✅ (done)

*The world becomes plural: several settlements, travel between them, and a
persistent save. Without this there is nothing to simulate.*

- **World model:** a `WorldGraph` (new service + `assets/data/world.json`)
  of locations (settlement, dungeon, POI) connected by routes with travel
  cost in ticks. `MapService` keys maps by location id.
- **Travel:** rebuild `WorldMapState` into the overworld travel screen:
  select a known, connected location → time advances by the route's ticks →
  arrive at the target map. (Portal `travel_ticks` already models this for
  intra-settlement transitions.)
- **More settlements:** 2–3 additional scenario JSONs (hamlet, town) —
  pure content. Parameterize `MapGenerator` only where the JSONs need it.
- **Save/Load:** freeze/thaw already serializes entities; extend it into a
  full JSON save (clock, player party, all map containers, world graph
  state). One save slot is enough for now. *A simulation without saves is
  untestable and unplayable.*

**Done when:** start in village A, open the world map, travel to town B
(clock jumps), trade-free walkabout there, save, quit, load, still in B.

*Shipped as:* `WorldGraphService` + `assets/data/world.json` (A1),
`MapGenerator.create_world()` + Eastmoor/Brackenfen scenarios (A2),
`WorldMapState` travel screen (A3), `SaveService` JSON snapshot on
F9/F10 (A4). Verified end-to-end by `tests/verify_world_travel.py` and
`tests/verify_save_load.py`.

### Phase B — The World Lives While You're Away (Off-screen Simulation) ✅ (done)

*The heart of the "more alive than Skyrim" claim.*

- **Abstract tick:** a `WorldSimulationService` advances every non-active
  location in coarse steps (e.g. once per in-game hour, not per turn).
  NPCs there don't pathfind — their abstract position *is* their scheduled
  activity ("at work", "in tavern", "asleep at home").
- **Arrival reconciliation:** on map enter, thaw entities but place
  schedule-bound NPCs where their *current* schedule entry says they should
  be — not where they were frozen. (Today NPCs wake up mid-stride wherever
  the player left them; this is the single most visible "the world waited
  for you" artifact.)
- **World chronicle:** an append-only event log per location (births of
  events only: "wolves attacked the herd", "merchant arrived", "feast day").
  Starts with a small set of random/seasonal events. This log is the raw
  material for rumors and generated quests later — build it early, keep it
  dumb.

**Done when:** leave village A at 08:00 with the smith at his anvil, travel
2 days, return — the smith is wherever 14:00 puts him, and the notice/log
shows at least one thing that happened in between.

*Shipped as:* `WorldSimulationService.reconcile_arrivals()` hooked into
`MapTransitionService` (B1; threshold `SIM_RECONCILE_MIN_TICKS` protects
short door hops) and `WorldChronicleService` + `world_events.json` (B2;
"Word around town" arrival log, saved in the snapshot). Verified by
`tests/verify_world_simulation.py` and `tests/verify_world_chronicle.py`.
NPC positions are not continuously simulated — they are derived from the
schedule at arrival time, which is the cheap two-level model working as
designed.

### Phase C — Trade & Economy

*First system where the simulation becomes tangibly useful to the player.*

- **Currency & value:** `value` field on item templates; gold on the player
  (and NPCs).
- **Merchant component + trade window:** shopkeeper NPCs get a stocked
  `Inventory` + `Merchant` component; bump-interaction on a merchant offers
  Talk/Trade; new `TradeWindow` (Recipe F) for buy/sell.
- **Local prices:** each settlement gets simple produce/consume rates per
  good (data in the scenario JSON). The off-screen tick (Phase B) moves
  stock levels; price = f(stock). Buy fish cheap at the coast, sell it
  inland — trade routes emerge from data, not scripting.

**Done when:** the player can earn gold by hauling goods between two
settlements whose prices differ for simulated reasons.

### Phase D — NPC Depth: Needs & Relationships

- **Needs:** a `Needs` component (sleep, food, social, work). Schedules
  remain the default day plan; needs can override (a starving NPC leaves
  work to eat). Keep it utility-score simple — no GOAP.
- **Relationships & reputation:** `Relationship` values NPC↔player (and
  coarse NPC↔NPC). Reputation per settlement: helping people / crimes move
  it; merchants price accordingly, guards react accordingly.
- **Dialogue v2:** extend `dialogues.json` from random lines to
  condition-keyed lines (time of day, current activity, relationship tier,
  recent chronicle events). Same service, richer selection.

**Done when:** an NPC interrupts its schedule out of a need, and two
villagers talk differently to a beloved vs. notorious player.

### Phase E — Quests & Rumors

- **Quest model:** `quests.json` + `QuestLog` component + journal window.
  States: offered → active → complete/failed. Objective types to start:
  deliver, fetch, kill, visit.
- **Hand-authored quests first** (3–5) to harden the pipeline end-to-end.
- **Generated requests:** derive quest offers from simulation state — the
  smith lacking ore (Phase C stock) posts a delivery request; a chronicle
  "wolf attack" event (Phase B) becomes a hunt request. Small templates,
  filled from world state.
- **Rumors:** NPC smalltalk draws from the chronicle and from quest/secret
  hooks of *other* locations — the village talks about the town.

**Done when:** the player hears about a problem in another settlement
through a rumor, travels there, and resolves a generated quest whose cause
genuinely exists in the simulation.

### Phase F — Secrets & Exploration

- **POIs:** hidden locations on the world graph (ruins, caves, shrines),
  not shown on the travel map until discovered via rumor, document item or
  exploration.
- **On-map secrets:** hidden tiles/containers/passages found via the
  existing Investigate mode (perception-gated) — gives the stat a purpose.
- **Dungeon generator:** small procedural interior maps for POIs (the
  roguelike heart, now embedded in a living frame).

**Done when:** a rumor from Phase E leads to an undiscovered POI with a
hand-placed secret and a generated dungeon.

## 4. Recommended order & why

**A → B → C → D → E → F**, one phase at a time.

- A first: plural world + saving is the precondition for everything.
- B before C/D: the abstract tick is the spine; economy and needs are
  *consumers* of it.
- C before D: trade delivers player-visible value with modest scope and
  forces the stock/price data model that D and E reuse.
- E needs B (chronicle), C (economy gaps) and benefits from D (reputation).
- F last: secrets pay off most when rumors (E) can point at them.

Cross-cutting rules (every phase): follow the CLAUDE.md recipes, JSON
before code, tests per system (`tests/verify_*.py`), one commit per task,
keep the abstract tick cheap (budget: no per-turn cost for inactive maps).

## 5. Open decisions (to settle when their phase starts)

| Decision | Options | Leaning |
|---|---|---|
| Overworld travel | node-graph travel screen vs. walkable overworld map | node-graph (cheaper, fits tick-time; walkable overworld can come later) |
| Save format | single JSON snapshot vs. per-map files | single JSON snapshot first |
| Economy granularity | per-good stock per settlement vs. abstract wealth | per-good stock (needed for generated delivery quests) |
| NPC needs scope | all NPCs vs. named NPCs only | named NPCs only at first (guards/extras stay schedule-only) |
