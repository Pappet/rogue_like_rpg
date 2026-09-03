"""Rest/wait duration options and time math (QoL: passing time).

Stateless helpers around passing time: which durations the RestWindow offers
(in ticks), and what the player is told once a rest is over. The fast-forward
itself belongs to ``TurnOrchestrator.advance_turns`` — this module decides
*how long* each preset skips and reports *what happened*.
"""

import esper

from config import DAY_START, TICKS_PER_HOUR, GameEvent, LogCategory

# Full daylight — the hour "Sleep until morning" targets.
MORNING_HOUR = DAY_START


def ticks_until_hour(clock, hour: int) -> int:
    """Ticks from the current clock time until the next occurrence of `hour`.

    Always returns a positive number; if it is already past `hour` today the
    result rolls over to that hour tomorrow.
    """
    current = clock.hour * TICKS_PER_HOUR + clock.minute
    target = (hour % 24) * TICKS_PER_HOUR
    delta = target - current
    if delta <= 0:
        delta += 24 * TICKS_PER_HOUR
    return delta


def wait_options() -> list[tuple[str, int]]:
    """Short on-the-spot waits offered by the ACTIONS-list 'Wait'."""
    return [
        ("Wait 1 hour", TICKS_PER_HOUR),
        ("Wait 2 hours", 2 * TICKS_PER_HOUR),
    ]


def sleep_options(clock) -> list[tuple[str, int]]:
    """Longer rests offered by a bed or innkeeper, including 'until morning'."""
    options = [
        ("Sleep 1 hour", TICKS_PER_HOUR),
        ("Sleep 2 hours", 2 * TICKS_PER_HOUR),
        ("Sleep 4 hours", 4 * TICKS_PER_HOUR),
    ]
    until_morning = ticks_until_hour(clock, MORNING_HOUR)
    # Offer it only from evening through early morning: skip the near-zero
    # case (already morning) and the all-day case (it's daytime, so the next
    # morning is ~a full day away — sleeping that long makes no sense).
    if TICKS_PER_HOUR // 2 <= until_morning <= 14 * TICKS_PER_HOUR:
        options.append((f"Sleep until morning ({MORNING_HOUR:02d}:00)", until_morning))
    return options


def report(clock, result: dict) -> None:
    """Tell the player what a completed rest actually did.

    ``result`` is what ``TurnOrchestrator.advance_turns`` returns: how many
    ticks really elapsed, and whether something cut the rest short.
    """
    if result["elapsed"] <= 0:
        esper.dispatch_event(
            GameEvent.LOG_MESSAGE, "[color=red]You can't rest right now.[/color]", None, LogCategory.ALERT
        )
        return
    esper.dispatch_event(GameEvent.LOG_MESSAGE, f"Time passes... it is now {clock.hour:02d}:{clock.minute:02d}.")
    if result["interrupted"]:
        esper.dispatch_event(
            GameEvent.LOG_MESSAGE, "[color=red]Something interrupts your rest![/color]", None, LogCategory.ALERT
        )
