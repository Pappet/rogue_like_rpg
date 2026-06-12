"""Rest/wait duration options and time math (QoL: passing time).

Stateless helpers that turn the world clock into the set of selectable
durations (in ticks) shown by the RestWindow. The actual fast-forward of
game time is driven by ``TurnOrchestrator.advance_turns``; this module only
decides *how long* each preset skips.
"""

from config import DAY_START, TICKS_PER_HOUR

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
