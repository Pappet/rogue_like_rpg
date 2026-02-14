# Phase 10: Entity & Map Templates - Research

**Researched:** 2026-02-14
**Domain:** Data-Driven Entity Factory & Map Prefab Loading
**Confidence:** HIGH

## Summary

Phase 10 extends the data-driven architecture established in Phase 9 to cover two more content domains: entities and map prefabs. Entity creation currently uses hardcoded factory functions (e.g., `entities/monster.py:create_orc`) that directly inline all stats and renderables. Map structures (houses, rooms) are procedurally assembled in `MapService` using pure Python logic. Both domains need to move toward external JSON configuration and factory pattern instantiation.

The entity side requires three deliverables: (1) an `entities.json` data file defining each entity template (stats, renderable, component list), (2) a loader in `ResourceLoader` (already existing as the right place) or a new `EntityRegistry`, and (3) an `EntityFactory` that reads templates from the registry and calls `world.create_entity()` with the correct components. The map prefab side requires a file format (JSON strongly preferred for consistency with tiles) that encodes a 2D grid of `type_id` strings plus optional entity spawn points, and a loader that converts this into a `MapLayer` placed at given coordinates.

The codebase is well-prepared: `TileRegistry`/`ResourceLoader` patterns are proven and tested. `esper` ECS is already in use; `world.create_entity(*components)` is the idiomatic call. The `MapService` already holds all the map manipulation logic, making it the natural home for a `load_prefab()` method. The primary risk is scope creep — the factory pattern and prefab loading are independent features; they should be planned and executed as separate sub-plans.

**Primary recommendation:** Mirror the `TileRegistry`/`ResourceLoader` pattern exactly for entities (new `EntityRegistry` + `ResourceLoader.load_entities()`), and add a `MapService.load_prefab()` that reads a JSON prefab file and stamps tiles onto an existing `MapLayer` at given coordinates.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` | Python Std | Data Serialization | Already in use for `tile_types.json`; consistent with Phase 9 pattern. |
| `dataclasses` | Python Std | EntityTemplate container | Already in use for `TileType`; zero new dependencies. |
| `esper` | In use | ECS world | `esper.create_entity(*components)` is the factory call target. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typing` | Python Std | Type hints on loaders and registries | Always — keeps code readable and IDE-friendly. |
| `os` | Python Std | File existence checks | Already used in `ResourceLoader.load_tiles()`. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSON for prefabs | TXT grid format (e.g. ASCII map files) | TXT is human-editable but harder to attach metadata (entity spawns, layer IDs). JSON wins for consistency. |
| Separate `EntityRegistry` | Reusing `TileRegistry` for everything | Entity templates are structurally different from `TileType`; separate registry avoids conflation of concepts. |
| New `EntityFactory` service | Adding factory method to `PartyService` | `PartyService` is party-specific; a generic `EntityFactory` serves all entity types (monsters, NPCs, items). |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

```
assets/data/
├── tile_types.json          # Existing - Phase 9
├── entities.json            # NEW - entity templates
└── prefabs/                 # NEW - map prefab files
    ├── cottage_interior.json
    └── tavern_interior.json

entities/
├── monster.py               # Existing - to be REPLACED/DEPRECATED by factory
├── entity_registry.py       # NEW - EntityTemplate dataclass + EntityRegistry
└── entity_factory.py        # NEW - EntityFactory.create(world, template_id, x, y)

services/
├── resource_loader.py       # EXTENDED - add load_entities() static method
└── map_service.py           # EXTENDED - add load_prefab() method
```

### Pattern 1: EntityTemplate Flyweight (mirrors TileType)

**What:** `EntityTemplate` is a dataclass holding shared, immutable entity definitions. `EntityRegistry` is a class-level dict singleton. `ResourceLoader.load_entities()` populates it during startup.
**When to use:** Whenever creating any non-player entity. The factory looks up the template by ID and builds the correct component list.

**Example (from codebase analysis of existing `TileType` pattern):**
```python
# entities/entity_registry.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

@dataclass
class EntityTemplate:
    id: str
    name: str
    sprite: str
    color: Tuple[int, int, int]
    sprite_layer: str          # e.g. "ENTITIES" — converted to SpriteLayer enum at load time
    hp: int
    max_hp: int
    power: int
    defense: int
    mana: int
    max_mana: int
    perception: int
    intelligence: int
    ai: bool = True
    blocker: bool = True
    components: List[str] = field(default_factory=list)  # optional extra component tags


class EntityRegistry:
    _registry: Dict[str, EntityTemplate] = {}

    @classmethod
    def register(cls, template: EntityTemplate) -> None:
        cls._registry[template.id] = template

    @classmethod
    def get(cls, template_id: str) -> Optional[EntityTemplate]:
        return cls._registry.get(template_id)

    @classmethod
    def clear(cls) -> None:
        cls._registry.clear()
```

### Pattern 2: EntityFactory (factory method over ECS)

**What:** `EntityFactory.create(world, template_id, x, y)` fetches the template, builds component instances, and calls `world.create_entity()`.
**When to use:** All non-player entity creation. Replaces `create_orc()`, `create_goblin()` etc.

```python
# entities/entity_factory.py
from config import SpriteLayer
from ecs.components import Position, Renderable, Stats, Name, Blocker, AI
from entities.entity_registry import EntityRegistry

class EntityFactory:
    @staticmethod
    def create(world, template_id: str, x: int, y: int) -> int:
        template = EntityRegistry.get(template_id)
        if template is None:
            raise ValueError(
                f"Entity template '{template_id}' not found in EntityRegistry. "
                "Ensure ResourceLoader.load_entities() has been called."
            )
        layer_enum = SpriteLayer[template.sprite_layer]
        components = [
            Position(x, y),
            Renderable(template.sprite, layer_enum.value, template.color),
            Stats(
                hp=template.hp, max_hp=template.max_hp,
                power=template.power, defense=template.defense,
                mana=template.mana, max_mana=template.max_mana,
                perception=template.perception, intelligence=template.intelligence,
            ),
            Name(template.name),
        ]
        if template.blocker:
            components.append(Blocker())
        if template.ai:
            components.append(AI())
        return world.create_entity(*components)
```

### Pattern 3: ResourceLoader Extension (load_entities)

**What:** Add `ResourceLoader.load_entities(filepath)` as a static method following the exact same structure as `load_tiles()`.
**When to use:** Called during `Game.startup()` after `load_tiles()`, before any entity creation.

```python
# services/resource_loader.py — new static method
@staticmethod
def load_entities(filepath: str) -> None:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Entity resource file not found: '{filepath}'.")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Entity resource file must contain a JSON array.")
    for item in data:
        for required in ("id", "name", "sprite", "sprite_layer", "hp", "max_hp",
                         "power", "defense", "mana", "max_mana", "perception", "intelligence"):
            if required not in item:
                raise ValueError(f"Entity entry missing required field '{required}': {item}")
        raw_color = item.get("color", [255, 255, 255])
        template = EntityTemplate(
            id=item["id"],
            name=item["name"],
            sprite=item["sprite"],
            color=tuple(raw_color),
            sprite_layer=item["sprite_layer"],
            hp=item["hp"], max_hp=item["max_hp"],
            power=item["power"], defense=item["defense"],
            mana=item["mana"], max_mana=item["max_mana"],
            perception=item["perception"], intelligence=item["intelligence"],
            ai=bool(item.get("ai", True)),
            blocker=bool(item.get("blocker", True)),
            components=item.get("components", []),
        )
        EntityRegistry.register(template)
```

### Pattern 4: Map Prefab Loading (MapService.load_prefab)

**What:** A JSON prefab file encodes a 2D array of `type_id` strings. An optional `"entities"` key holds spawn points. `MapService.load_prefab()` reads the file and stamps tiles onto an existing `MapLayer` at an offset `(ox, oy)`.
**When to use:** Whenever a pre-designed room or structure (cottage interior, dungeon room) needs to be placed on a map layer. Replaces inline `draw_rectangle` compositions in `create_village_scenario` / `add_house_to_map`.

**Prefab JSON schema:**
```json
{
  "id": "cottage_interior",
  "width": 10,
  "height": 10,
  "tiles": [
    ["wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone"],
    ["wall_stone", "floor_stone", "floor_stone", "floor_stone", "floor_stone", "floor_stone", "floor_stone", "floor_stone", "floor_stone", "wall_stone"],
    ["..."],
    ["wall_stone", "wall_stone", "wall_stone", "door_stone",  "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone", "wall_stone"]
  ],
  "entities": [
    {"template_id": "orc", "x": 3, "y": 3}
  ]
}
```

**Loader method:**
```python
# services/map_service.py — new method
def load_prefab(self, world, layer: MapLayer, filepath: str, ox: int = 0, oy: int = 0) -> None:
    """Stamps a JSON prefab onto an existing MapLayer at offset (ox, oy).
    Optionally spawns entities defined in the prefab."""
    import json, os
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Prefab file not found: '{filepath}'.")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    tile_rows = data.get("tiles", [])
    for row_idx, row in enumerate(tile_rows):
        for col_idx, type_id in enumerate(row):
            tx, ty = ox + col_idx, oy + row_idx
            if 0 <= ty < layer.height and 0 <= tx < layer.width:
                layer.tiles[ty][tx].set_type(type_id)
    for spawn in data.get("entities", []):
        EntityFactory.create(world, spawn["template_id"], ox + spawn["x"], oy + spawn["y"])
```

### Anti-Patterns to Avoid

- **Hardcoded component lists in factory callers:** Do not pass `hp=10, power=3` at the call site. All stats must come from the template. The factory is the single source of truth.
- **Using `create_orc()` alongside `EntityFactory.create()`:** Once the factory exists, all callers must be migrated. Leaving `create_orc()` in place creates two code paths that diverge silently.
- **Prefab loading that creates new `Tile` objects:** Use `tile.set_type(type_id)` on existing tiles (as `draw_rectangle` does) rather than constructing new `Tile` instances and inserting them. This preserves per-instance visibility state correctly.
- **Calling `load_entities()` after map creation:** Both `load_tiles()` and `load_entities()` must be called during `Game.startup()` before any map or entity creation occurs. The current `main.py` calls `create_village_scenario()` before `load_tiles()`; this ordering bug must be fixed simultaneously.

---

## Current State Assessment (codebase audit)

### What exists today:

| Item | File | State |
|------|------|-------|
| Entity creation | `entities/monster.py` | Hardcoded factory function `create_orc(world, x, y)`. All stats inline. |
| Entity creation (player) | `services/party_service.py` | Inline `esper.create_entity(...)` with hardcoded values. |
| Monster spawning | `services/map_service.py:spawn_monsters()` | Calls `create_orc(world, x, y)` directly. |
| Map structure generation | `services/map_service.py:add_house_to_map()` | Calls `draw_rectangle()` in code; no external data file. |
| `ResourceLoader` | `services/resource_loader.py` | Has `load_tiles()` only. Ready to be extended. |
| `TileRegistry` | `map/tile_registry.py` | Proven singleton pattern. Mirror for entities. |
| JSON data dir | `assets/data/` | Has `tile_types.json`. Add `entities.json` and `prefabs/` subdirectory. |
| `load_tiles()` call site | `main.py` | **MISSING** — `load_tiles()` is never called in `main.py`. The `create_village_scenario` works because tests call it separately. This is a latent bug that must be fixed. |

### Critical finding: `load_tiles()` is not called in `main.py`

Inspecting `main.py`: `ResourceLoader.load_tiles()` is never invoked. `GameController.__init__` calls `self.map_service.create_village_scenario(world)` directly. The only reason the game runs is that the tests (`verify_resource_loader.py`, `verify_tile_refactor.py`) call `ResourceLoader.load_tiles()` as part of their setup, but this is not present in the production startup path.

**Implication for Phase 10:** The plan must include fixing this ordering bug. Both `load_tiles()` and the new `load_entities()` must be called in `GameController.__init__()` (or in `Game.startup()`) before any map or entity creation.

---

## JSON Schema Definitions

### `assets/data/entities.json`

```json
[
  {
    "id": "orc",
    "name": "Orc",
    "sprite": "O",
    "color": [0, 255, 0],
    "sprite_layer": "ENTITIES",
    "hp": 10,
    "max_hp": 10,
    "power": 3,
    "defense": 0,
    "mana": 0,
    "max_mana": 0,
    "perception": 5,
    "intelligence": 5,
    "ai": true,
    "blocker": true
  }
]
```

Fields map 1:1 to the existing `Stats`, `Renderable`, `Name`, `Blocker`, `AI` components. No component structure changes are required.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON parsing | Custom string splitter | `json.load()` | Already in use; handles all edge cases. |
| Component dispatch | if/elif chain checking template flags | Direct conditional component append | The component set per entity type is small and stable. Enum-based dispatch is over-engineering at this scale. |
| Prefab coordinate mapping | Custom coordinate system | Offset `(ox, oy)` added to each tile position | Simple, no abstraction needed. `draw_rectangle` already uses this. |
| Entity serialization | Custom save format for templates | The registry IS the template; instances are ECS components | Templates are stateless data definitions, not runtime state. |

---

## Common Pitfalls

### Pitfall 1: Startup Ordering — Registry not populated before use
**What goes wrong:** `EntityFactory.create()` raises `ValueError` because `EntityRegistry` is empty. Or `Tile(type_id=...)` raises because `TileRegistry` is empty.
**Why it happens:** `ResourceLoader.load_tiles()` and `ResourceLoader.load_entities()` are not called before map/entity creation. Currently `main.py` does not call `load_tiles()` at all.
**How to avoid:** Add both `ResourceLoader.load_tiles("assets/data/tile_types.json")` and `ResourceLoader.load_entities("assets/data/entities.json")` at the very top of `GameController.__init__()`, before `create_village_scenario()`.
**Warning signs:** `ValueError: Tile type 'floor_stone' not found in TileRegistry` at startup.

### Pitfall 2: Prefab tile stamping creates NEW Tile objects instead of mutating
**What goes wrong:** `layer.tiles[y][x] = Tile(type_id=type_id)` — this discards the existing tile's `visibility_state`. A tile that was previously `VISIBLE` or `SHROUDED` becomes `UNEXPLORED` after a prefab is stamped over it.
**Why it happens:** Confusion between `Tile` construction and `Tile.set_type()`.
**How to avoid:** Always use `layer.tiles[ty][tx].set_type(type_id)` when stamping prefabs. Only create new `Tile` objects when initializing a fresh layer.
**Warning signs:** Fog of war resets when entering a known room.

### Pitfall 3: `create_orc()` is still called after EntityFactory is introduced
**What goes wrong:** Two code paths exist: the factory-driven path and the legacy `create_orc()` path. Stat changes in `entities.json` are silently ignored for entities spawned via `create_orc()`.
**Why it happens:** Incomplete migration — `map_service.py:spawn_monsters()` still calls `create_orc()`.
**How to avoid:** After `EntityFactory` and `EntityRegistry` are in place, update `spawn_monsters()` to call `EntityFactory.create(world, "orc", x, y)` and delete `entities/monster.py`.

### Pitfall 4: `SpriteLayer` enum conversion omitted in entity loader
**What goes wrong:** `Renderable` is created with the string `"ENTITIES"` instead of the integer `SpriteLayer.ENTITIES.value`.
**Why it happens:** The entity loader stores `sprite_layer` as a raw string. The factory must convert it via `SpriteLayer[template.sprite_layer].value`.
**How to avoid:** Perform the `SpriteLayer[layer_name]` lookup in `EntityFactory.create()` (at creation time) rather than at load time. This mirrors the approach in `resource_loader.py` which converts sprite layer strings for tiles.

### Pitfall 5: Prefab file path is relative, breaks from different working directories
**What goes wrong:** `open("assets/data/prefabs/cottage.json")` fails when the test is run from a subdirectory.
**How to avoid:** Use `os.path.join(os.path.dirname(__file__), "../../assets/data/prefabs/...")` or always pass absolute paths. Adopt the same convention as `ResourceLoader.load_tiles()` which takes a full filepath argument from the caller.

---

## Code Examples

### Verified current entity creation (to be replaced)
```python
# entities/monster.py — current implementation
def create_orc(world, x, y):
    orc = world.create_entity()
    world.add_component(orc, Position(x, y))
    world.add_component(orc, Renderable(sprite="O", color=(0, 255, 0), layer=SpriteLayer.ENTITIES.value))
    world.add_component(orc, Stats(hp=10, max_hp=10, power=3, defense=0, mana=0, max_mana=0, perception=5, intelligence=5))
    world.add_component(orc, Name("Orc"))
    world.add_component(orc, Blocker())
    world.add_component(orc, AI())
    return orc
```

### Verified existing `draw_rectangle` (model for prefab stamping)
```python
# map/map_generator_utils.py — verified at line 32
def draw_rectangle(layer, x, y, w, h, type_id, filled=False):
    for i in range(y, y + h):
        for j in range(x, x + w):
            if 0 <= i < rows and 0 <= j < cols:
                is_border = (i == y or i == y + h - 1 or j == x or j == x + w - 1)
                if filled or is_border:
                    layer.tiles[i][j].set_type(type_id)  # <-- mutates, preserves visibility
```

### Verified esper entity creation API
```python
# game_states.py — verified pattern at line 11 (party_service.py)
player_entity = esper.create_entity(
    Position(x, y),
    Renderable("@", SpriteLayer.ENTITIES.value, (255, 255, 255)),
    Stats(hp=100, max_hp=100, ...),
    Name("Player"),
    Inventory(),
)
# esper.create_entity(*components) accepts varargs of component instances
```

---

## Sub-Plan Breakdown Recommendation

This phase has two logically independent features that should be separate sub-plans:

**Sub-plan 10-01: Entity Templates & Factory (DATA-003 + ARCH-004)**
1. Create `assets/data/entities.json` with at least `orc` template.
2. Create `entities/entity_registry.py` with `EntityTemplate` dataclass and `EntityRegistry` singleton.
3. Extend `services/resource_loader.py` with `load_entities()` static method.
4. Create `entities/entity_factory.py` with `EntityFactory.create()`.
5. Fix `main.py` to call `load_tiles()` and `load_entities()` at startup.
6. Migrate `services/map_service.py:spawn_monsters()` to use `EntityFactory`.
7. Delete `entities/monster.py` (or deprecate and stub).
8. Write `tests/verify_entity_factory.py`.

**Sub-plan 10-02: Map Prefab Loading (DATA-002)**
1. Create `assets/data/prefabs/` directory.
2. Define prefab JSON schema and create at least one prefab file (e.g., `cottage_interior.json`).
3. Add `MapService.load_prefab(world, layer, filepath, ox, oy)` method.
4. Optionally refactor `add_house_to_map()` to use prefab loading for at least one house type.
5. Write `tests/verify_prefab_loading.py`.

**Dependency:** 10-01 should precede 10-02, because prefab entity spawning relies on `EntityFactory`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `create_orc(world, x, y)` hardcoded | `EntityFactory.create(world, "orc", x, y)` from JSON | Phase 10 | Entity stats changeable without code changes. |
| `add_house_to_map()` pure code | `load_prefab("cottage.json", layer, ox, oy)` | Phase 10 | Map designers can edit rooms without Python knowledge. |
| `ResourceLoader` has only `load_tiles()` | `ResourceLoader` has `load_tiles()` + `load_entities()` | Phase 10 | Consistent loading pattern for all registry types. |

---

## Open Questions

1. **Should `PartyService` (player) also use `EntityFactory`?**
   - What we know: The player has many unique components (`ActionList`, `Inventory`, `TurnOrder`) that no enemy shares.
   - What's unclear: Whether a "player" template in `entities.json` makes sense, or if the player's unique setup should remain in `PartyService`.
   - Recommendation: Keep `PartyService` separate for Phase 10. The factory is for generic/non-player entities. Document this as a deferred item.

2. **Should `entities.json` support arbitrary component tags?**
   - What we know: The `EntityTemplate` could have a `components: List[str]` field (e.g., `["LightSource"]`) to trigger optional component attachment.
   - What's unclear: How to instantiate components with parameters (e.g., `LightSource(radius=3)`) from a string tag alone.
   - Recommendation: For Phase 10, only support the fixed component set (`Stats`, `Renderable`, `Position`, `Name`, `Blocker`, `AI`). Parameterized optional components are a future concern.

3. **Should prefab files include stair/portal definitions?**
   - What we know: `add_house_to_map()` creates stair portals as ECS entities. Prefabs currently only define tile layouts.
   - What's unclear: Whether portal data belongs in the prefab or in the map service code.
   - Recommendation: For Phase 10, keep portal/stair creation in `MapService` code. Prefabs provide tile layout only, plus simple entity spawns from `EntityFactory`. Portal templating is a more advanced feature.

---

## Sources

### Primary (HIGH confidence)
- `/home/peter/Projekte/rogue_like_rpg/entities/monster.py` — Current hardcoded entity creation; exact component set verified.
- `/home/peter/Projekte/rogue_like_rpg/services/resource_loader.py` — Existing loader pattern; verified 85 lines, static method structure.
- `/home/peter/Projekte/rogue_like_rpg/map/tile_registry.py` — Registry singleton pattern to mirror; verified 52 lines.
- `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — All component dataclasses; verified exact field names for `Stats`, `Renderable`, `Position`, `Name`, `Blocker`, `AI`.
- `/home/peter/Projekte/rogue_like_rpg/services/map_service.py` — Current `add_house_to_map()` and `spawn_monsters()` implementations; verified callers.
- `/home/peter/Projekte/rogue_like_rpg/map/map_generator_utils.py` — `draw_rectangle` uses `set_type()`; exact pattern for prefab stamping.
- `/home/peter/Projekte/rogue_like_rpg/main.py` — Confirmed `load_tiles()` is NOT called; startup ordering bug verified.
- `/home/peter/Projekte/rogue_like_rpg/.planning/phases/09-data-driven-core/09-VERIFICATION.md` — Phase 9 verification confirms all 6 truths passed; pattern is solid foundation.

### Secondary (MEDIUM confidence)
- esper ECS documentation — `esper.create_entity(*components)` vararg signature verified in use across `party_service.py` and `game_states.py`.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — same libraries as Phase 9, no new dependencies.
- Architecture: HIGH — direct mirror of TileRegistry/ResourceLoader pattern, verified working in Phase 9.
- Pitfalls: HIGH — discovered from direct codebase audit (startup ordering bug is real, not hypothetical).
- Prefab format: MEDIUM — JSON schema is a design choice; no external constraint; straightforward given existing tile ID system.

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable codebase; no fast-moving dependencies)
