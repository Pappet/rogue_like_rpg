# Phase 15: AI Component Foundation - Context

**Gathered:** 2026-02-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Define the ECS data structures (enums, dataclasses, component fields) that every downstream AI system depends on, and wire them into entity creation via the JSON template pipeline. No behavior logic — just the data foundation.

</domain>

<decisions>
## Implementation Decisions

### Default behavior states
- Hostile enemies (orcs) start in WANDER state — they roam until they spot the player
- Friendly NPCs default depends on type — configurable per JSON entity template
- Default state comes from JSON template field, not hardcoded per type
- Fallback if template doesn't specify: WANDER (everything moves by default)

### Hostility model
- Replace simple boolean with Alignment enum: HOSTILE, NEUTRAL, FRIENDLY
- Alignment is a string enum (Alignment.HOSTILE = "hostile") — readable in JSON and logs
- Alignment is mutable at runtime — enables future taming, provocation, faction shifts
- Alignment comes from JSON entity template, consistent with default_state
- NEUTRAL behavior in v1.2: Claude's discretion (simplest approach, likely same as FRIENDLY for now)

### State enum design
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

### Entity template wiring
- JSON template specifies AI behavior fields (JSON shape at Claude's discretion — nested vs flat)
- Only entities with existing AI marker get AIBehaviorState — portals, items, corpses unaffected (Claude verifies in codebase)
- Invalid state/alignment values in JSON fail loudly at entity creation — catch data bugs early

### Claude's Discretion
- JSON structure shape (nested "ai" object vs top-level fields) — pick what fits existing patterns
- NEUTRAL alignment behavior in v1.2 (likely treat as FRIENDLY)
- Exact fields on ChaseData and WanderData stubs
- Which entities currently have AI marker (Claude reads codebase to confirm)

</decisions>

<specifics>
## Specific Ideas

- The data-driven JSON pipeline pattern is established: data file → ResourceLoader → Registry → Factory. AI behavior config should follow this same flow.
- String enums were chosen for readability in JSON templates and debug logs — both AIState and Alignment.
- Separate components per state mirrors ECS best practice and enables clean attach/detach on transitions.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 15-ai-component-foundation*
*Context gathered: 2026-02-14*
