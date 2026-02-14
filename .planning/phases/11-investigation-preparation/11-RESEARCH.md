# Phase 11: Investigation Preparation - Research

**Researched:** 2026-02-14
**Domain:** ECS Description Component (Dynamic, Context-Aware Text)
**Confidence:** HIGH

## Summary

Phase 11 has four success criteria. Criteria 1-3 (Registry Loaded, Prefab Map, Template Entity) are already fully implemented and verified as of Phase 10 completion (9/9 tests passing). The only new engineering work required is criterion 4: implementing a `Description` ECS component that returns context-aware text when queried (MECH-006).

The `Description` component must satisfy two behavioral requirements: (a) return a static base description for healthy entities (e.g., "A generic orc"), and (b) return a different description when the entity is in a specific state such as wounded (e.g., "A wounded orc"). The component must be queryable — something must call it with access to the entity's current state to produce the appropriate string. Since this is a Python ECS project using simple dataclasses as components, the cleanest pattern is a dataclass with a `get(stats)` method that encapsulates the conditional logic.

No new libraries are required. The component lives in `ecs/components.py` alongside all existing components. `EntityFactory.create()` must be extended to attach a `Description` component when the entity template includes description fields. The `entities.json` file for the orc must be extended with description fields. A verification test in the pattern of existing tests confirms the behavior.

**Primary recommendation:** Implement `Description` as a dataclass with `base: str`, optional `wounded_text: str`, and an optional `wounded_threshold: float` (fraction of max_hp). Add a `get(stats) -> str` method that returns `wounded_text` if `stats.hp / stats.max_hp <= wounded_threshold`, otherwise returns `base`. Extend `EntityTemplate`, `ResourceLoader.load_entities()`, and `EntityFactory.create()` minimally to pass description fields through the pipeline.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `dataclasses` | Python Std | Description component container | Already used for all components in `ecs/components.py`. |
| `typing` | Python Std | Type hints | Already used throughout codebase. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | In use | Verification tests | Pattern established across all prior phases. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dataclass with `get(stats)` method | Pure callable stored in component | A stored callable (lambda) cannot be serialized or inspected. A method on the class is clear, testable, and consistent with the codebase style. |
| Dataclass with `get(stats)` method | Separate `DescriptionSystem` processor | A system adds overhead and indirection for a trivial read operation. The component is data + a single pure function; no system is needed. |
| Inline logic in `get()` | External rules table / strategy pattern | Over-engineering for two states (healthy/wounded). Simple if-branch in `get()` is sufficient and readable. |

**Installation:** No new packages required.

---

## Architecture Patterns

### Recommended Project Structure

```
ecs/
└── components.py        # ADD Description dataclass here

entities/
├── entity_registry.py   # EXTEND EntityTemplate with description fields
├── entity_factory.py    # EXTEND create() to attach Description component

assets/data/
└── entities.json        # EXTEND orc entry with description fields

services/
└── resource_loader.py   # EXTEND load_entities() to parse description fields

tests/
└── verify_description.py  # NEW verification test file
```

### Pattern 1: Description Component as Dataclass with Method

**What:** A dataclass holding description strings and a `get(stats)` method that evaluates which string to return based on current health.
**When to use:** Whenever a system or UI code needs to display a description for an entity.

```python
# ecs/components.py — new component
from dataclasses import dataclass, field

@dataclass
class Description:
    base: str
    wounded_text: str = ""
    wounded_threshold: float = 0.5  # HP fraction at or below which wounded_text applies

    def get(self, stats) -> str:
        """Return context-aware description based on entity stats.

        Args:
            stats: A Stats component instance with .hp and .max_hp fields.

        Returns:
            wounded_text if hp/max_hp <= wounded_threshold and wounded_text is set,
            otherwise base.
        """
        if self.wounded_text and stats.max_hp > 0:
            if stats.hp / stats.max_hp <= self.wounded_threshold:
                return self.wounded_text
        return self.base
```

### Pattern 2: EntityTemplate Extension (minimal fields)

**What:** Add three optional fields to `EntityTemplate` to carry description data from JSON through the registry to the factory.
**When to use:** Always — the factory reads these to build the `Description` component.

```python
# entities/entity_registry.py — extend EntityTemplate
@dataclass
class EntityTemplate:
    # ... existing fields ...
    description: str = ""
    wounded_text: str = ""
    wounded_threshold: float = 0.5
```

### Pattern 3: EntityFactory Extension (attach Description)

**What:** After building the existing component list, append a `Description` component if `template.description` is non-empty.
**When to use:** Whenever a template defines a description.

```python
# entities/entity_factory.py — extend create()
from ecs.components import ..., Description

# Inside EntityFactory.create(), after building components list:
if template.description:
    components.append(
        Description(
            base=template.description,
            wounded_text=template.wounded_text,
            wounded_threshold=template.wounded_threshold,
        )
    )
```

### Pattern 4: ResourceLoader Extension (parse description fields)

**What:** Parse optional `"description"`, `"wounded_text"`, and `"wounded_threshold"` keys from each entity JSON entry and pass them to `EntityTemplate`.
**When to use:** In `ResourceLoader.load_entities()` alongside existing field parsing.

```python
# services/resource_loader.py — inside load_entities() loop
template = EntityTemplate(
    # ... existing fields ...
    description=item.get("description", ""),
    wounded_text=item.get("wounded_text", ""),
    wounded_threshold=float(item.get("wounded_threshold", 0.5)),
)
```

### Pattern 5: entities.json Extension

**What:** Add description fields to the orc entry.
**When to use:** For all entities that should have descriptions.

```json
{
  "id": "orc",
  "name": "Orc",
  "description": "A generic orc",
  "wounded_text": "A wounded orc",
  "wounded_threshold": 0.5,
  "...": "... existing fields ..."
}
```

### Anti-Patterns to Avoid

- **Storing a lambda in the component:** Lambdas cannot be serialized, compared in tests, or inspected cleanly. Use a plain method on the class instead.
- **Creating a DescriptionSystem to evaluate descriptions:** The `get(stats)` call is a pure read, not a game-tick mutation. Systems process state changes; a description lookup is not a system concern.
- **Hard-coding thresholds or strings in the factory:** All description data must come from the JSON template. The factory is a pass-through, not a logic layer.
- **Making `description` a required field:** Not all entities need descriptions. The field is optional with an empty-string default; the factory only attaches the component when `description` is non-empty.

---

## Current State Assessment (codebase audit)

All three prior success criteria are confirmed complete:

| Criterion | Status | Evidence |
|-----------|--------|---------|
| Registry Loaded | DONE | `main.py` lines 24-25: `ResourceLoader.load_tiles()` and `load_entities()` called at startup. 9/9 tests pass. |
| Prefab Map | DONE | `assets/data/prefabs/cottage_interior.json` exists. `MapService.load_prefab()` implemented and tested. |
| Template Entity | DONE | `EntityFactory.create(world, "orc", x, y)` used in `spawn_monsters()`. `entities.json` defines orc template. |
| Dynamic Description | NOT STARTED | `ecs/components.py` has no `Description` component. `EntityTemplate` has no description fields. |

The orc template in `entities.json` currently has no description fields:
```json
{"id": "orc", "name": "Orc", "sprite": "O", "color": [0, 255, 0], "sprite_layer": "ENTITIES",
 "hp": 10, "max_hp": 10, "power": 3, "defense": 0, "mana": 0, "max_mana": 0,
 "perception": 5, "intelligence": 5, "ai": true, "blocker": true}
```

The `ecs/components.py` file has 14 existing component dataclasses. `Description` is straightforward to add at the end.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Description state machine | Complex rules engine | Simple `if hp/max_hp <= threshold` branch | The spec requires exactly two states (generic / wounded). Over-engineering creates maintenance burden with no benefit. |
| Separate description file | New JSON format for descriptions | Add fields to `entities.json` | The JSON pipeline is established. Separate files for simple text data adds I/O and lookup complexity. |
| Dynamic string formatting with `%s` / `.format()` | Template string system | Plain conditional returning one of two strings | Placeholder syntax adds parsing complexity; the spec shows two discrete string values, not format strings. |

---

## Common Pitfalls

### Pitfall 1: `get()` called with no stats when entity has no Stats component
**What goes wrong:** Code calls `description.get(stats)` but the entity does not have a `Stats` component, causing an `AttributeError`.
**Why it happens:** Not all entities need stats (e.g., static objects). If Description is attached to a non-combat entity, `Stats` may be absent.
**How to avoid:** For Phase 11, only the orc (which always has `Stats`) uses Description. The test should confirm `Stats` is present on the orc. Document that `get()` callers must ensure the entity has `Stats`.
**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'hp'` when querying description.

### Pitfall 2: Division by zero in `get()` when `max_hp == 0`
**What goes wrong:** `stats.hp / stats.max_hp` raises `ZeroDivisionError` for entities with `max_hp = 0`.
**Why it happens:** Some entities (items, portals) may legitimately have `max_hp = 0`.
**How to avoid:** Guard with `if stats.max_hp > 0` before dividing. The code example above already includes this guard.
**Warning signs:** `ZeroDivisionError` when querying description for non-combat entities.

### Pitfall 3: Description component not attached because `description` field is empty string
**What goes wrong:** Developer adds description to JSON but forgets it; entity has no `Description` component; query raises `ComponentNotFound`.
**Why it happens:** The factory only attaches `Description` when `template.description` is non-empty.
**How to avoid:** Verify the orc entry in `entities.json` has a non-empty `"description"` field. The test should check `world.has_component(entity_id, Description)`.
**Warning signs:** `esper.ComponentNotFound` when querying `Description` for orc entity.

### Pitfall 4: `wounded_threshold` stored as int instead of float
**What goes wrong:** JSON value `0.5` parsed as int `0` due to missing `float()` cast, causing wounded text to never trigger.
**Why it happens:** `item.get("wounded_threshold", 0.5)` returns `0.5` as a Python float from JSON, but if someone writes `"wounded_threshold": 1` in JSON (integer), the comparison still works. However, explicit `float()` cast is safer and consistent with how `hp`/`max_hp` use `int()` casts.
**How to avoid:** Use `float(item.get("wounded_threshold", 0.5))` in the loader.
**Warning signs:** Wounded text never appears even when HP is low.

---

## Code Examples

Verified patterns from existing codebase:

### Existing component pattern (to mirror)
```python
# ecs/components.py — verified pattern, line 25 (Stats)
@dataclass
class Stats:
    hp: int
    max_hp: int
    power: int
    defense: int
    mana: int
    max_mana: int
    perception: int
    intelligence: int
```

### Existing EntityFactory.create() component assembly (to extend)
```python
# entities/entity_factory.py — verified, lines 42-64
components = [
    Position(x, y),
    Renderable(template.sprite, layer_value, template.color),
    Stats(hp=template.hp, max_hp=template.max_hp, ...),
    Name(template.name),
]
if template.blocker:
    components.append(Blocker())
if template.ai:
    components.append(AI())
return world.create_entity(*components)
```

### Existing optional field parsing in ResourceLoader (to mirror)
```python
# services/resource_loader.py — verified, lines 136-138
ai = bool(item.get("ai", True))
blocker = bool(item.get("blocker", True))
```

### Existing EntityTemplate optional fields (to extend)
```python
# entities/entity_registry.py — verified, lines 29-30
ai: bool = True
blocker: bool = True
```

### Description component (new)
```python
# ecs/components.py — new addition
@dataclass
class Description:
    base: str
    wounded_text: str = ""
    wounded_threshold: float = 0.5

    def get(self, stats) -> str:
        if self.wounded_text and stats.max_hp > 0:
            if stats.hp / stats.max_hp <= self.wounded_threshold:
                return self.wounded_text
        return self.base
```

### Verification test pattern (to follow)
```python
# tests/verify_description.py — pattern from verify_entity_factory.py
def test_description_get_returns_base_when_healthy():
    desc = Description(base="A generic orc", wounded_text="A wounded orc", wounded_threshold=0.5)
    stats = Stats(hp=10, max_hp=10, power=3, defense=0, mana=0, max_mana=0, perception=5, intelligence=5)
    assert desc.get(stats) == "A generic orc"

def test_description_get_returns_wounded_when_hp_low():
    desc = Description(base="A generic orc", wounded_text="A wounded orc", wounded_threshold=0.5)
    stats = Stats(hp=4, max_hp=10, ...)   # 40% HP — below 50% threshold
    assert desc.get(stats) == "A wounded orc"

def test_description_attached_to_orc_entity():
    # Setup registries, create orc via EntityFactory
    # Assert world.has_component(entity_id, Description)
    ...
```

---

## Sub-Plan Breakdown

Phase 11 is a single focused feature. It should be one sub-plan:

**Sub-plan 11-01: Description Component (MECH-006)**
1. Add `Description` dataclass with `get(stats)` method to `ecs/components.py`.
2. Add `description`, `wounded_text`, `wounded_threshold` optional fields to `EntityTemplate` in `entities/entity_registry.py`.
3. Extend `ResourceLoader.load_entities()` to parse the new optional fields.
4. Extend `EntityFactory.create()` to attach `Description` component when `template.description` is non-empty.
5. Add description fields to the orc entry in `assets/data/entities.json`.
6. Write `tests/verify_description.py` covering: healthy text, wounded text, boundary at exact threshold, no-description entity (no component attached), division-by-zero guard.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No entity descriptions | `Description` component with `get(stats)` method | Phase 11 | Entities can now express context-aware state to UI and investigation systems. |
| All entity components hardcoded | Components driven from `entities.json` | Phase 10 | Description data is in JSON — editable without Python changes. |

---

## Open Questions

1. **Should wounded_threshold be expressed as a fraction (0.5) or integer percent (50)?**
   - What we know: Existing `Stats` fields use integers for HP values. The threshold logic divides `hp / max_hp` producing a float.
   - What's unclear: Whether game designers prefer "0.5" or "50" in JSON.
   - Recommendation: Use fraction (0.0-1.0) stored as float. It matches the natural `hp/max_hp` arithmetic without a unit conversion step, and is standard in game dev for health thresholds.

2. **Should `Description.get()` accept `Stats` directly or the full entity ID for component lookup?**
   - What we know: Callers will have the entity ID and can retrieve `Stats` via `world.component_for_entity(entity_id, Stats)`. `Description.get(stats)` keeps the component decoupled from the world.
   - Recommendation: Accept `stats` directly (not entity ID or world). This keeps the component a pure function with no external dependencies — easier to test and compose.

3. **Should multiple description states be supported (e.g., "near death" at 10% HP)?**
   - What we know: The spec requires exactly two states: generic and wounded.
   - Recommendation: Implement exactly two states for Phase 11. If more states are needed later, the method can be extended to a list of `(threshold, text)` tuples.

---

## Sources

### Primary (HIGH confidence)
- `/home/peter/Projekte/rogue_like_rpg/ecs/components.py` — All 14 existing component dataclasses; exact pattern for Description.
- `/home/peter/Projekte/rogue_like_rpg/entities/entity_registry.py` — EntityTemplate with optional fields `ai` and `blocker`; exact pattern to extend for description fields.
- `/home/peter/Projekte/rogue_like_rpg/entities/entity_factory.py` — Component assembly in `create()`; confirmed conditional append pattern for optional components.
- `/home/peter/Projekte/rogue_like_rpg/services/resource_loader.py` — `load_entities()` optional field parsing with `item.get()`; pattern to extend.
- `/home/peter/Projekte/rogue_like_rpg/assets/data/entities.json` — Current orc entry; confirmed no description fields present.
- `/home/peter/Projekte/rogue_like_rpg/.planning/phases/10-entity-map-templates/10-VERIFICATION.md` — Confirmed 7/7 truths verified for Phase 10; criteria 1-3 of Phase 11 are already done.
- `pytest tests/verify_entity_factory.py tests/verify_prefab_loading.py` — 9/9 tests passing confirmed live.

### Secondary (MEDIUM confidence)
- esper ECS `world.has_component()` and `world.component_for_entity()` API — used in existing tests; pattern for verification test assertions.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; same Python stdlib + dataclasses as all prior phases.
- Architecture: HIGH — direct extension of established component pattern; verified against actual codebase.
- Pitfalls: HIGH — discovered from direct code analysis (division-by-zero guard, optional attachment condition).
- Description component design: HIGH — simple two-state conditional; spec is unambiguous.

**Research date:** 2026-02-14
**Valid until:** 2026-03-14 (stable codebase; no external dependencies)
