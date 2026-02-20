# Research: ScheduleSystem & Activity States

## Objective
Implement a system that wires NPC AI to follow their assigned schedules from `ScheduleRegistry`.

## Current State
- `WorldClockService` provides the current hour (0-23).
- `ScheduleRegistry` stores `ScheduleTemplate` which contains `ScheduleEntry` objects.
- `ScheduleEntry` has `start`, `end`, `activity`, and optional `target_pos`.
- `AIBehaviorState` handles high-level AI state (`WANDER`, `CHASE`, `IDLE`).
- `AISystem` follows `PathData` if present.
- `PathfindingService` can compute paths.

## Requirements
- `ScheduleSystem` processor to update NPC targets based on time.
- State transitions between activities (WORK, PATROL, SOCIALIZE, etc.).
- NPCs without schedules should still WANDER.
- Pathfinding triggered on activity change.

## Implementation Details

### 1. New Component: `CurrentActivity`
We need a way to track what an NPC is currently doing according to their schedule to avoid redundant checks and pathfinding calls every tick.

```python
@dataclass
class CurrentActivity:
    activity: str
    target_pos: Optional[Tuple[int, int]] = None
    entry_index: int = -1  # Index in the ScheduleTemplate.entries list
```

### 2. ScheduleSystem
A new `esper.Processor` that:
1. Iterates over entities with `Schedule` and `Position`.
2. Gets the current hour from `WorldClockService`.
3. Finds the matching `ScheduleEntry` in the `ScheduleTemplate`.
4. If the entry has changed:
   - Updates `CurrentActivity`.
   - If `target_pos` is provided and different from current position:
     - Triggers `PathfindingService` to update `PathData`.
   - If no `target_pos` is provided, maybe it defaults to `WANDER` or `IDLE` at current location?
   - Updates `AIBehaviorState.state` based on the activity? Or should we add new states to `AIState`?

### 3. Expanding `AIState`
The roadmap mentions WORK, PATROL, SOCIALIZE. These could be added to `AIState` or they could be meta-states that determine if the NPC should WANDER or IDLE at their destination.

If we add them to `AIState`, we need to update `AISystem._dispatch` to handle them.
Alternatively, if they just mean "Go here and then IDLE" or "Go here and then WANDER", we might not need new states in `AIState`.
However, "PATROL" might mean something specific.

For now, I'll assume we might need:
- `AIState.WORK` (IDLE at target?)
- `AIState.PATROL` (WANDER at target?)
- `AIState.SOCIALIZE` (IDLE/WANDER at target?)
- `AIState.SLEEP` (Wait, Phase 32 is Sleep, so maybe not yet).

Actually, the roadmap for Phase 31 says:
"NPCs transition between states (WORK, PATROL, SOCIALIZE, etc.) according to schedule."

### 4. Integration with AISystem
`AISystem` already handles `PathData`. If `ScheduleSystem` sets `PathData`, `AISystem` will move the NPC.
Once `PathData` is empty (destination reached), the `AISystem` should know what to do next based on the current activity.

If `behavior.state` is set by `ScheduleSystem`, `AISystem` will use its match statement.

## Open Questions
- Should `ScheduleSystem` run every tick or only when the clock advances?
  - `WorldClockService.advance` is called every player turn. So `ScheduleSystem` should run every enemy turn (or just before it).
- How to handle multiple entries for the same hour? (Assume first match or strictly disjoint intervals).
- What if an NPC is in `CHASE` state?
  - Usually, `CHASE` should override `Schedule`. If a hostile NPC sees the player, it should stop its schedule and chase. Once it loses the player, it should resume its schedule.

## Proposed Strategy
1. Add `Activity` related components.
2. Update `AIState` enum with common activity states.
3. Implement `ScheduleSystem` to manage transitions.
4. Update `AISystem` to handle new states and prioritize `ScheduleSystem`'s target-seeking.
5. Ensure `CHASE` behavior still overrides scheduled activities.
