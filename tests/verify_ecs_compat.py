"""Regression tests for the esper 3.7 compatibility shim (core/ecs.py).

esper 3.7's private ``_get_components`` has a faulty smallest-set
optimisation that drops a requested component type out of its membership
filter while still dereferencing it, raising ``KeyError`` for entities that
lack that type. ``apply_esper_compat_patches()`` replaces it with a correct
implementation. These tests pin the exact shape that crashed the game so a
future esper bump (or an accidental revert of the shim) is caught.
"""

from dataclasses import dataclass

import esper

from core.ecs import apply_esper_compat_patches


@dataclass
class _Needs:
    v: int = 0


@dataclass
class _Activity:
    v: int = 0


@dataclass
class _AIBehaviorState:
    v: int = 0


@dataclass
class _Position:
    v: int = 0


def test_multi_query_does_not_keyerror_on_partial_entity():
    """The exact in-game trigger: a live "guard" (AIBehaviorState + Activity +
    Position, no Needs) with set sizes |AIB| < |Needs| < |Activity| < |Position|
    must not raise KeyError and must be excluded from the four-component query.
    """
    apply_esper_compat_patches()

    guard = esper.create_entity(_AIBehaviorState(), _Activity(), _Position())
    esper.create_entity(_Needs(), _Activity(), _Position())
    esper.create_entity(_Needs(), _Activity(), _Position())
    esper.create_entity(_Position())

    # |AIB|=1 < |Needs|=2 < |Activity|=3 < |Position|=4 — the crashing shape.
    assert len(esper._components[_AIBehaviorState]) == 1
    assert len(esper._components[_Needs]) == 2
    assert len(esper._components[_Activity]) == 3
    assert len(esper._components[_Position]) == 4

    result = esper.get_components(_Needs, _Activity, _AIBehaviorState, _Position)

    # Guard lacks Needs, so nothing matches all four — and no KeyError is raised.
    assert result == []
    # The guard is still found by a query it genuinely satisfies.
    assert [e for e, _ in esper.get_components(_Activity, _AIBehaviorState, _Position)] == [guard]


def test_multi_query_returns_full_matches():
    """Entities that have every requested component are returned correctly,
    regardless of the relative set sizes that drive the optimisation.
    """
    apply_esper_compat_patches()

    full = esper.create_entity(_Needs(), _Activity(), _AIBehaviorState(), _Position())
    esper.create_entity(_AIBehaviorState(), _Position())  # smallest-ish, partial
    esper.create_entity(_Position())

    result = esper.get_components(_Needs, _Activity, _AIBehaviorState, _Position)
    assert [e for e, _ in result] == [full]
    ent, (needs, activity, behavior, pos) = result[0]
    assert isinstance(needs, _Needs)
    assert isinstance(activity, _Activity)
    assert isinstance(behavior, _AIBehaviorState)
    assert isinstance(pos, _Position)
