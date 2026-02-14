# Phase 15: AI Component Foundation - Research

**Researched:** 2026-02-14
**Domain:** Python ECS (esper) — component data structures, string enums, JSON template pipeline
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Default behavior states**
- Hostile enemies (orcs) start in WANDER state — they roam until they spot the player
- Friendly NPCs default depends on type — configurable per JSON entity template
- Default state comes from JSON template field, not hardcoded per type
- Fallback if template doesn't specify: WANDER (everything moves by default)

**Hostility model**
- Replace simple boolean with Alignment enum: HOSTILE, NEUTRAL, FRIENDLY
- Alignment is a string enum (Alignment.HOSTILE = "hostile") — readable in JSON and logs
- Alignment is mutable at runtime — enables future taming, provocation, faction shifts
- Alignment comes from JSON entity template, consistent with default_state
- NEUTRAL behavior in v1.2: Claude's discretion (simplest approach, likely same as FRIENDLY for now)

**State enum design**
- AIState is a string enum: AIState.WANDER = "wander", AIState.CHASE = "chase", etc.
- States: IDLE, WANDER, CHASE, TALK (TALK is non-operational placeholder)
- State-specific data lives in separate ECS components (not on AIBehaviorState)
  - ChaseData component for chase target coordinates, turns chasing
  - WanderData component for wander-specific state
  - Attach/detach on state transition — ECS-pure pattern
- All data components (AIBehaviorState, ChaseData, WanderData) defined in Phase 15 as stubs
  - AIBehaviorState: state field (AIState)
  - ChaseData: last_known_x, last_known_y, turns_without_sight (fields TBD by planner)
  - WanderData: fields TBD by planner

**Entity template wiring**
- JSON template specifies AI behavior fields (JSON shape at Claude's discretion — nested vs flat)
- Only entities with existing AI marker get AIBehaviorState — portals, items, corpses unaffected (Claude verifies in codebase)
- Invalid state/alignment values in JSON fail loudly at entity creation — catch data bugs early

### Claude's Discretion
- JSON structure shape (nested "ai" object vs top-level fields) — pick what fits existing patterns
- NEUTRAL alignment behavior in v1.2 (likely treat as FRIENDLY)
- Exact fields on ChaseData and WanderData stubs
- Which entities currently have AI marker (Claude reads codebase to confirm)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

---

## Summary

Phase 15 operates entirely within the existing codebase — no new libraries are required. The work is surgical: add three new dataclasses and two enums to `ecs/components.py`, extend `EntityTemplate` with two new fields, update `ResourceLoader.load_entities()` to parse those fields, and update `EntityFactory.create()` to attach `AIBehaviorState` when the entity's `ai` flag is true.

The codebase already has a clean, validated pattern for this. The tile pipeline (tile_types.json → TileRegistry → TileType) and the entity pipeline (entities.json → EntityRegistry → EntityTemplate → EntityFactory) are both well-established. The AI component additions follow the same pattern: add template fields, parse them in ResourceLoader, conditionally attach components in EntityFactory.

The only non-trivial design question is how to handle validation of string-enum values from JSON (e.g., "wander" must map to a valid AIState). The existing codebase raises `ValueError` on bad data in ResourceLoader — the new code should match that pattern exactly.

**Primary recommendation:** Add `AIState` and `Alignment` as `str, Enum` subclasses to `ecs/components.py`, extend `EntityTemplate` with `default_state: str` and `alignment: str`, update `ResourceLoader.load_entities()` to parse these with validation, and update `EntityFactory.create()` to attach `AIBehaviorState` (plus stub `ChaseData`/`WanderData` classes).

---

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Python stdlib `enum.Enum` | stdlib | Base class for enums | Already used for `SpriteLayer`, `GameStates` in `config.py` |
| Python stdlib `dataclasses.dataclass` | stdlib | Component structs | All existing ECS components use `@dataclass` |
| `esper` | in use | ECS world management | Already the project ECS; `esper.has_component`, `esper.add_component` pattern established |

### No New Libraries Needed
This phase is pure data structure work. All tools are already imported and in use.

---

## Architecture Patterns

### Existing Project Structure (relevant files)
```
ecs/
  components.py          # All ECS component dataclasses live here — ADD enums + new components HERE
  world.py               # esper wrapper
  systems/
    death_system.py      # Removes AI component on death — must also remove AIBehaviorState + ChaseData/WanderData
entities/
  entity_registry.py     # EntityTemplate flyweight — ADD default_state, alignment fields HERE
  entity_factory.py      # Creates entities from templates — ADD AIBehaviorState attachment HERE
services/
  resource_loader.py     # Parses JSON → registry — ADD parsing for default_state, alignment HERE
assets/data/
  entities.json          # Entity template data — ADD default_state, alignment fields to orc entry
```

### Pattern 1: String Enums (matches existing project style)
**What:** Enum subclasses that inherit from both `str` and `Enum`, giving values that are readable strings.
**When to use:** When enum values appear in JSON, debug logs, or need to compare to raw strings without `.value`.
**Example:**
```python
# Source: config.py uses IntEnum-style Enum; this is str variant used for JSON readability
from enum import Enum

class AIState(str, Enum):
    IDLE = "idle"
    WANDER = "wander"
    CHASE = "chase"
    TALK = "talk"

class Alignment(str, Enum):
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"

# Usage — these compare equal to their string values:
assert AIState.WANDER == "wander"  # True with str, Enum
# In JSON: "default_state": "wander" → AIState("wander") → AIState.WANDER
```

**Why `str, Enum` over plain `Enum`:** `AIState("wander")` works as a constructor from a raw string (e.g., from JSON), whereas plain `Enum` requires `AIState["WANDER"]` (key lookup by name) or the value directly. The constructor form is cleaner for JSON parsing.

### Pattern 2: ECS Dataclass Components (existing project pattern)
**What:** Marker and data components as `@dataclass` classes in `ecs/components.py`.
**Example:**
```python
# Source: ecs/components.py — existing pattern
from dataclasses import dataclass

@dataclass
class AIBehaviorState:
    state: AIState
    alignment: Alignment

@dataclass
class ChaseData:
    last_known_x: int
    last_known_y: int
    turns_without_sight: int = 0

@dataclass
class WanderData:
    pass  # stub — fields added in future phases as needed
```

### Pattern 3: Conditional Component Attachment in EntityFactory (existing project pattern)
**What:** Factory checks template boolean flags before attaching optional components.
**Example:**
```python
# Source: entities/entity_factory.py — existing pattern for Blocker and AI
if template.ai:
    components.append(AI())
    # NEW: also attach AIBehaviorState
    state = AIState(template.default_state)
    alignment = Alignment(template.alignment)
    components.append(AIBehaviorState(state=state, alignment=alignment))
```

### Pattern 4: Loud Validation in ResourceLoader (existing project pattern)
**What:** ResourceLoader raises `ValueError` with descriptive messages for invalid data. New AI fields follow the same contract.
**Example:**
```python
# Source: services/resource_loader.py — existing pattern
# Validate and parse default_state
raw_state = item.get("default_state", "wander")
try:
    AIState(raw_state)  # Validates the string is a valid AIState value
except ValueError:
    raise ValueError(
        f"Entity '{item['id']}' has invalid default_state '{raw_state}'. "
        f"Valid values: {[s.value for s in AIState]}"
    )

raw_alignment = item.get("alignment", "hostile")
try:
    Alignment(raw_alignment)
except ValueError:
    raise ValueError(
        f"Entity '{item['id']}' has invalid alignment '{raw_alignment}'. "
        f"Valid values: {[a.value for a in Alignment]}"
    )
```

### Pattern 5: Flat JSON Fields (recommendation — matches existing entities.json style)
**What:** The existing `entities.json` uses flat top-level keys (no nested objects). New AI fields should follow the same flat structure.
**Recommendation:** Use `"default_state"` and `"alignment"` as flat top-level fields rather than a nested `"ai": {}` object. This is consistent with how `"blocker"`, `"ai"`, `"description"` are all top-level.
**Example:**
```json
{
  "id": "orc",
  "name": "Orc",
  "ai": true,
  "default_state": "wander",
  "alignment": "hostile",
  ...
}
```

### Anti-Patterns to Avoid
- **Storing state in EntityTemplate:** `EntityTemplate` is a flyweight (immutable shared data). It stores the *default* state string, not a live `AIState` instance. The live `AIState` value belongs on the `AIBehaviorState` ECS component attached to the specific entity.
- **Hardcoding alignment per entity type:** Alignment must come from JSON, not from `if template.id == "orc": hostile`. The whole point is data-driven configuration.
- **Using `Enum` (not `str, Enum`) for JSON-facing enums:** Plain `Enum` requires `.value` to get the string, making JSON round-trips awkward. `str, Enum` lets the enum value compare directly to strings.
- **Converting AIState/Alignment inside EntityTemplate:** ResourceLoader stores raw strings in `EntityTemplate` (consistent with how `sprite_layer` is stored as raw string). The conversion to enum happens in `EntityFactory.create()`, matching the existing pattern.

---

## Codebase Facts (Verified by Direct Reading)

### Entities that currently have the AI marker
**Source: Direct codebase read, 2026-02-14**

Only entities with `"ai": true` in `entities.json` get the `AI()` component via `EntityFactory`. Currently confirmed:

| Entity | Has `"ai": true` | Has AI() component |
|--------|-----------------|-------------------|
| `orc` | YES (in entities.json) | YES |
| Portals | NO — created directly in `map_service.py` with `Portal` component, no AI | NO |
| Corpses | Created by `DeathSystem` from dying entities — `AI` component is *removed* on death | NO |
| Items | No item entities in codebase yet (only `Inventory` component exists) | NO |

**Conclusion:** Only `orc` currently gets `AI()`. Phase 15 should attach `AIBehaviorState` to all entities where `template.ai is True`. This matches the CONTEXT.md constraint.

### DeathSystem impact
`DeathSystem.on_entity_died()` removes `[Blocker, AI, Stats]` when an entity dies (line 29 in `death_system.py`). After Phase 15, it should also remove `AIBehaviorState`, `ChaseData`, and `WanderData` from that list. This is a required update in Phase 15 scope — otherwise corpses will retain AIBehaviorState.

### EntityTemplate field storage pattern
`ResourceLoader` stores `sprite_layer` as a raw string in `EntityTemplate` (not converted to enum). Conversion to `SpriteLayer` enum happens in `EntityFactory`. The new `default_state` and `alignment` fields should follow this exact same pattern — store raw strings in `EntityTemplate`, convert to `AIState`/`Alignment` in `EntityFactory`.

### Import pattern
`EntityFactory` imports components at the top: `from ecs.components import Position, Renderable, Stats, Name, Blocker, AI, Description`. The new components `AIBehaviorState, AIState, Alignment, ChaseData, WanderData` should be added to this import.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| String-to-enum conversion with error | Custom `if/elif` chain | `AIState(raw_string)` — raises `ValueError` on invalid input automatically | Enum constructor already validates and raises descriptive error |
| JSON field validation | Custom string checks | Try/except around `AIState(raw_state)` | Reuses Python's built-in enum validation |

**Key insight:** Python's `str, Enum` constructor already does all the validation needed. `AIState("invalid")` raises `ValueError: 'invalid' is not a valid AIState`. Wrap it in a try/except and re-raise with context — no hand-rolled validation logic needed.

---

## Common Pitfalls

### Pitfall 1: Forgetting to Update DeathSystem
**What goes wrong:** Corpses retain `AIBehaviorState`, `ChaseData`, `WanderData` after death because `DeathSystem` only removes `[Blocker, AI, Stats]`.
**Why it happens:** The new components exist in Phase 15 but `DeathSystem` was written before them.
**How to avoid:** Add `AIBehaviorState`, `ChaseData`, `WanderData` to the component removal list in `DeathSystem.on_entity_died()`. Use `esper.has_component()` check first (same pattern as existing code).
**Warning signs:** Dead orc still appears in `esper.get_component(AIBehaviorState)` queries.

### Pitfall 2: EntityTemplate Stores Live Enum Instances
**What goes wrong:** `EntityTemplate` is a flyweight — all entities of type "orc" share the same template instance. If `default_state` is stored as `AIState.WANDER` (a mutable Python object reference), and something modifies it, all orcs are affected.
**Why it happens:** Temptation to convert strings to enums early (in ResourceLoader) for convenience.
**How to avoid:** Store `default_state: str` and `alignment: str` on `EntityTemplate` (raw strings). Convert to enums in `EntityFactory` when creating each individual entity's `AIBehaviorState`.
**Warning signs:** Test changes one entity's alignment, another entity's template shows the change.

### Pitfall 3: `AIState` Import Missing in DeathSystem/Tests
**What goes wrong:** `DeathSystem` or tests fail with `NameError` because `AIBehaviorState` is imported from the wrong place or not at all.
**Why it happens:** Adding new components to `ecs/components.py` doesn't auto-update imports in systems.
**How to avoid:** After adding to `ecs/components.py`, update all files that need to reference the new types: `entity_factory.py` (import), `death_system.py` (import + removal list), and any new test files.

### Pitfall 4: JSON Validation Only at Load Time vs. Runtime
**What goes wrong:** Entities spawned without going through ResourceLoader (e.g., legacy `create_orc()` in `entities/monster.py`) don't get `AIBehaviorState`.
**Why it happens:** `entities/monster.py` creates orcs by hand using `world.add_component()` — it bypasses `EntityFactory` entirely.
**How to avoid:** Either update `create_orc()` in `monster.py` to also attach `AIBehaviorState`, or note it as a known limitation. The file appears to be legacy and may not be used in production paths (main.py uses `EntityFactory` via map_service). Verify and document which path is active.
**Warning signs:** Orc created via `create_orc()` fails `esper.has_component(ent, AIBehaviorState)`.

---

## Code Examples

### String Enum Definition (recommended pattern)
```python
# Source: Python docs + codebase pattern from config.py
# Place in: ecs/components.py

from enum import Enum

class AIState(str, Enum):
    IDLE = "idle"
    WANDER = "wander"
    CHASE = "chase"
    TALK = "talk"

class Alignment(str, Enum):
    HOSTILE = "hostile"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
```

### New ECS Components
```python
# Source: existing ecs/components.py pattern
# Place in: ecs/components.py

@dataclass
class AIBehaviorState:
    state: AIState
    alignment: Alignment

@dataclass
class ChaseData:
    last_known_x: int
    last_known_y: int
    turns_without_sight: int = 0

@dataclass
class WanderData:
    pass  # Stub — no fields needed until wander behavior system is implemented
```

### EntityTemplate Extension
```python
# Source: entities/entity_registry.py — existing EntityTemplate dataclass
# Additions to EntityTemplate:

@dataclass
class EntityTemplate:
    # ... existing fields ...
    default_state: str = "wander"   # raw string, converted to AIState in EntityFactory
    alignment: str = "hostile"      # raw string, converted to Alignment in EntityFactory
```

### ResourceLoader Extension (load_entities)
```python
# Source: services/resource_loader.py — follow existing ai/blocker optional field pattern

# After parsing ai and blocker:
raw_state = item.get("default_state", "wander")
try:
    AIState(raw_state)  # validate — raises ValueError if invalid
except ValueError:
    raise ValueError(
        f"Entity '{item['id']}' has invalid default_state '{raw_state}'. "
        f"Valid values: {[s.value for s in AIState]}"
    )

raw_alignment = item.get("alignment", "hostile")
try:
    Alignment(raw_alignment)  # validate
except ValueError:
    raise ValueError(
        f"Entity '{item['id']}' has invalid alignment '{raw_alignment}'. "
        f"Valid values: {[a.value for a in Alignment]}"
    )

template = EntityTemplate(
    # ... existing fields ...,
    default_state=raw_state,
    alignment=raw_alignment,
)
```

### EntityFactory Extension
```python
# Source: entities/entity_factory.py — follow existing conditional component pattern

if template.ai:
    components.append(AI())
    components.append(AIBehaviorState(
        state=AIState(template.default_state),
        alignment=Alignment(template.alignment),
    ))
```

### DeathSystem Update
```python
# Source: ecs/systems/death_system.py — extend existing component removal list

for component_type in [Blocker, AI, Stats, AIBehaviorState, ChaseData, WanderData]:
    if esper.has_component(entity, component_type):
        esper.remove_component(entity, component_type)
```

### JSON Template Update (entities.json)
```json
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
  "default_state": "wander",
  "alignment": "hostile",
  "blocker": true,
  "description": "A generic orc",
  "wounded_text": "A wounded orc",
  "wounded_threshold": 0.5
}
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `ai: bool` on EntityTemplate, `AI()` marker component | Keep `ai: bool` + `AI()` — add `AIBehaviorState` alongside | AI marker stays for system queries; `AIBehaviorState` adds behavior data |
| No hostility concept | `Alignment` enum with HOSTILE/NEUTRAL/FRIENDLY | Replaces implicit "all AI entities are hostile" assumption |
| No state tracking | `AIBehaviorState.state: AIState` | Enables downstream behavior systems to branch on state |

---

## Open Questions

1. **Should `entities/monster.py` be updated or marked deprecated?**
   - What we know: `create_orc()` in `monster.py` creates an orc by hand, bypassing `EntityFactory`. It does not appear in `main.py` or `map_service.py` — only in legacy test files.
   - What's unclear: Whether any runtime code path still calls `create_orc()` directly.
   - Recommendation: Mark as legacy in a comment, do not update it. Add a note in tests that `create_orc()` is a legacy helper and does not attach `AIBehaviorState`. The production spawn path is `EntityFactory.create()`.

2. **WanderData fields: what to stub?**
   - What we know: WanderData is a stub in Phase 15 — no behavior system consumes it yet. CONTEXT.md says "fields TBD by planner."
   - What's unclear: Whether any downstream phase needs specific fields pre-declared.
   - Recommendation: `WanderData` with `pass` body is cleanest. Add a docstring: "Stub component marking entity as currently wandering. Fields added in wander behavior phase." This satisfies ECS attach/detach pattern without guessing future fields.

---

## Sources

### Primary (HIGH confidence)
- Direct codebase read: `ecs/components.py` — all existing component patterns verified
- Direct codebase read: `entities/entity_registry.py` — EntityTemplate flyweight structure confirmed
- Direct codebase read: `entities/entity_factory.py` — conditional component attachment pattern confirmed
- Direct codebase read: `services/resource_loader.py` — validation pattern (try/except + ValueError) confirmed
- Direct codebase read: `assets/data/entities.json` — flat field structure confirmed
- Direct codebase read: `ecs/systems/death_system.py` — AI component removal on death confirmed
- Direct codebase read: `config.py` — existing `Enum` usage pattern (SpriteLayer, GameStates) confirmed

### Secondary (MEDIUM confidence)
- Python `str, Enum` pattern: well-established Python stdlib idiom for JSON-friendly enums. Verified via knowledge of Python enum documentation and consistent with existing `Enum` usage in config.py.

### Tertiary (LOW confidence)
- None — all findings grounded in direct codebase reads.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by direct codebase read; no new libraries
- Architecture: HIGH — all patterns confirmed by reading existing production code
- Pitfalls: HIGH — DeathSystem interaction verified by reading death_system.py directly; EntityTemplate flyweight pattern verified by reading entity_registry.py

**Research date:** 2026-02-14
**Valid until:** Stable — no external libraries; valid until codebase changes (recommend re-verify before planning if >30 days pass)
