"""Tests for rest_service: duration option building and time math."""

from config import TICKS_PER_HOUR
from game.services import rest_service


class _Clock:
    def __init__(self, hour, minute=0):
        self.hour = hour
        self.minute = minute


def test_ticks_until_hour_same_day():
    clock = _Clock(hour=2, minute=0)  # 02:00
    assert rest_service.ticks_until_hour(clock, 7) == 5 * TICKS_PER_HOUR


def test_ticks_until_hour_accounts_for_minutes():
    clock = _Clock(hour=2, minute=30)
    assert rest_service.ticks_until_hour(clock, 3) == 30  # half an hour left


def test_ticks_until_hour_rolls_over_past_target():
    clock = _Clock(hour=10, minute=0)  # already past 07:00
    # Next 07:00 is tomorrow: 21 hours away.
    assert rest_service.ticks_until_hour(clock, 7) == 21 * TICKS_PER_HOUR


def test_wait_options_are_short():
    options = rest_service.wait_options()
    assert [ticks for _label, ticks in options] == [TICKS_PER_HOUR, 2 * TICKS_PER_HOUR]


def test_sleep_options_include_until_morning_at_night():
    clock = _Clock(hour=1, minute=0)  # deep night
    options = rest_service.sleep_options(clock)
    labels = [label for label, _ in options]
    assert any("until morning" in label for label in labels)
    # The until-morning option should skip to 07:00 = 6 hours.
    morning = next(ticks for label, ticks in options if "until morning" in label)
    assert morning == 6 * TICKS_PER_HOUR


def test_sleep_options_skip_until_morning_when_already_morning():
    clock = _Clock(hour=7, minute=0)  # exactly morning
    labels = [label for label, _ in rest_service.sleep_options(clock)]
    assert not any("until morning" in label for label in labels)
