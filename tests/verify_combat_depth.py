"""Combat depth: crits, bleeding, attack abilities (ROADMAP Phase G5).

Critical hits double damage and open a bleeding wound; Bleeding ticks
once per round via the StatusEffectSystem; Power Strike routes through
the normal CombatSystem with a power multiplier.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import AttackIntent, Bleeding, Name, Position, Stats
from game.systems.combat_system import CombatSystem
from game.systems.status_effect_system import StatusEffectSystem


class _Rng:
    """Stub rng with a scripted random() sequence."""

    def __init__(self, *values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0) if self.values else 0.99


def _fighter(power=5, defense=1, hp=20):
    return esper.create_entity(
        Name("Fighter"),
        Position(1, 1, 0),
        Stats(hp=hp, max_hp=hp, power=power, defense=defense, mana=0, max_mana=0, perception=5, intelligence=5),
    )


# ---------------------------------------------------------------------------
# Crits & multipliers
# ---------------------------------------------------------------------------


def test_normal_hit_unchanged_without_crit():
    attacker, target = _fighter(power=5), _fighter(defense=1)
    esper.add_component(attacker, AttackIntent(target_entity=target))

    CombatSystem(rng=_Rng(0.99)).process()

    assert esper.component_for_entity(target, Stats).hp == 16  # 5 - 1 = 4
    assert not esper.has_component(target, Bleeding)


def test_critical_hit_doubles_damage_and_causes_bleeding():
    attacker, target = _fighter(power=5), _fighter(defense=1)
    esper.add_component(attacker, AttackIntent(target_entity=target))

    CombatSystem(rng=_Rng(0.0)).process()  # crit roll passes

    assert esper.component_for_entity(target, Stats).hp == 12  # (5-1)*2 = 8
    assert esper.has_component(target, Bleeding)


def test_power_multiplier_scales_the_hit():
    attacker, target = _fighter(power=5), _fighter(defense=1)
    esper.add_component(attacker, AttackIntent(target_entity=target, power_multiplier=2.0))

    CombatSystem(rng=_Rng(0.99)).process()

    assert esper.component_for_entity(target, Stats).hp == 11  # 5*2 - 1 = 9


def test_zero_damage_hits_cannot_crit():
    attacker, target = _fighter(power=1), _fighter(defense=5)
    esper.add_component(attacker, AttackIntent(target_entity=target))

    CombatSystem(rng=_Rng(0.0)).process()

    assert esper.component_for_entity(target, Stats).hp == 20
    assert not esper.has_component(target, Bleeding)


# ---------------------------------------------------------------------------
# Bleeding ticks
# ---------------------------------------------------------------------------


def test_bleeding_ticks_once_per_round_and_expires():
    ent = _fighter(hp=10)
    esper.add_component(ent, Bleeding(damage_per_turn=1, turns_left=3))
    system = StatusEffectSystem()

    for expected_hp in (9, 8, 7):
        system.process()
        assert esper.component_for_entity(ent, Stats).hp == expected_hp

    assert not esper.has_component(ent, Bleeding), "the wound must close after its duration"
    system.process()
    assert esper.component_for_entity(ent, Stats).hp == 7, "no more bleeding after expiry"


def test_bleeding_out_dispatches_entity_died():
    ent = _fighter(hp=1)
    esper.add_component(ent, Bleeding(damage_per_turn=1, turns_left=3))
    died = []

    # esper keeps handlers as weak references — the function must stay alive
    def on_died(entity, attacker=None):
        died.append(entity)

    esper.set_handler("entity_died", on_died)

    StatusEffectSystem().process()

    assert died == [ent], "bleeding out must kill"


# ---------------------------------------------------------------------------
# Power Strike is a player action
# ---------------------------------------------------------------------------


def test_player_has_power_strike_action():
    import json

    with open("assets/data/player.json") as f:
        data = json.load(f)
    strike = next((a for a in data["actions"] if a["name"] == "Power Strike"), None)
    assert strike is not None
    assert strike["power_multiplier"] > 1.0
    assert strike["cost_mana"] > 0
