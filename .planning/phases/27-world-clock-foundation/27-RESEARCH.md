# Phase 27: WorldClock Foundation - Research

**Researched:** 2026-02-16
**Domain:** Timekeeping, Turn Loop Integration, UI Header
**Confidence:** HIGH

## Summary

This phase implements a central `WorldClockService` to track in-game time (ticks, hours, days). Time advances on each player turn and during map transitions (travel time). The clock drives time-of-day phases (DAWN, DAY, DUSK, NIGHT), which will later influence rendering and AI. The service will be integrated into the existing `TurnSystem` and `Game` state to ensure consistency between the "Round" counter and global world time.

**Primary recommendation:** Use a standalone `WorldClockService` persisted in `GameController.persist` and synchronize it with `TurnSystem.round_counter` so that map aging and time-based effects remain in sync.

## User Constraints

No `CONTEXT.md` was found for this phase. Research followed the requirements listed in the phase goal.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `WorldClockService` | N/A | Time tracking | Custom logic for game-specific time phases |
| `esper` | 3.7 | Event Dispatching | Built-in event system for notifying state changes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` | Python 3 | Data structures | For time state and component updates |

**Installation:**
No new packages required. `esper` is already installed.

## Architecture Patterns

### Recommended Project Structure
```
services/
└── world_clock_service.py # Core timekeeping logic
ecs/
└── components.py          # Updated with Portal travel_ticks
ecs/systems/
├── turn_system.py         # Hook to advance clock on turn end
└── ui_system.py           # Updated to display time in header
```

### Pattern 1: Synchronized Time (Source of Truth)
The `WorldClockService.total_ticks` and `TurnSystem.round_counter` must be kept in sync. 
- **Rule:** `round_counter = total_ticks + 1`.
- **Implementation:** `TurnSystem` can either derive its round counter from the clock or they both advance together. To minimize refactoring of existing map-aging logic, both should be advanced explicitly during travel.

### Pattern 2: Time-of-Day Phases
Phases are derived from the current hour using configurable boundaries in `config.py`.
- **DAWN:** Transitions from Night to Day.
- **DAY:** Full visibility.
- **DUSK:** Transitions from Day to Night.
- **NIGHT:** Reduced visibility (to be implemented in Phase 28).

### Anti-Patterns to Avoid
- **Hardcoded Boundaries:** Avoid hardcoding 5 AM, 8 AM, etc., in the logic. Use constants in `config.py`.
- **Redundant Event Loops:** Don't create a separate "TimeSystem" processor if the clock only advances on turns. The service call inside `TurnSystem` is sufficient.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Event Bus | Custom observer pattern | `esper.dispatch_event` | Esper already provides a lightweight, integrated event system. |
| Time Logic | Real-time `pygame` timers | Turn-based tick counter | Game time is discrete (per-action), not continuous. |

## Common Pitfalls

### Pitfall 1: Out-of-Sync Counters
**What goes wrong:** `TurnSystem.round_counter` increments by 1, but `WorldClock` is skipped (or vice versa) during map transitions.
**Why it happens:** Map transitions happen outside the normal turn loop.
**How to avoid:** Create a helper or ensure `Game.transition_map` updates both.

### Pitfall 2: Midnight Transition
**What goes wrong:** Hour logic like `if hour > NIGHT_START and hour < DAWN_START` fails because 23 > 5 but 0 < 5.
**Why it happens:** Circular math for 24-hour clocks.
**How to avoid:** Use `if hour >= NIGHT_START or hour < DAWN_START` or a list of phase ranges.

## Code Examples

### WorldClockService Implementation
```python
# services/world_clock_service.py
import esper

class WorldClockService:
    def __init__(self, ticks_per_hour=60, total_ticks=0):
        self.ticks_per_hour = ticks_per_hour
        self.total_ticks = total_ticks

    @property
    def hour(self):
        return (self.total_ticks // self.ticks_per_hour) % 24

    @property
    def day(self):
        return (self.total_ticks // (self.ticks_per_hour * 24)) + 1

    @property
    def minute(self):
        return (self.total_ticks % self.ticks_per_hour) * (60 // self.ticks_per_hour)

    def get_phase(self):
        from config import DAWN_START, DAY_START, DUSK_START, NIGHT_START
        h = self.hour
        if DAWN_START <= h < DAY_START: return "DAWN"
        if DAY_START <= h < DUSK_START: return "DAY"
        if DUSK_START <= h < NIGHT_START: return "DUSK"
        return "NIGHT"

    def advance(self, amount=1):
        self.total_ticks += amount
        esper.dispatch_event("clock_tick", self.get_state())

    def get_state(self):
        return {
            "total_ticks": self.total_ticks,
            "day": self.day,
            "hour": self.hour,
            "minute": self.minute,
            "phase": self.get_phase()
        }
```

### TurnSystem Hook
```python
# ecs/systems/turn_system.py
def end_player_turn(self):
    self.current_state = GameStates.ENEMY_TURN
    # Advance clock by 1 tick
    if hasattr(self, 'world_clock'):
        self.world_clock.advance(1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `round_counter` only | `WorldClockService` | Phase 27 | Enables day/night cycles and schedules. |
| Instant Map Change | Travel Duration | Phase 27 | World ages realistically during travel. |

## Open Questions

1. **How many ticks per hour?**
   - Recommendation: Use 60 (1 tick = 1 minute). This makes "1 step = 1 minute" which is a standard Rogue-like abstraction.
2. **Should the clock advance during 'inspect' actions?**
   - Recommendation: No. Requirement CLK-01 says "advances on each player turn". Currently, `inspect` (Targeting mode) does not end the player's turn until an action is confirmed or canceled. If inspection is "free", time doesn't move.

## Sources

### Primary (HIGH confidence)
- `ecs/systems/turn_system.py` - Current turn logic.
- `game_states.py` - Map transition logic.
- `esper` documentation - Event system usage.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Simple Python services.
- Architecture: HIGH - Fits current `persist` pattern.
- Pitfalls: HIGH - Logic for circular time is standard.

**Research date:** 2026-02-16
**Valid until:** 2026-03-18
