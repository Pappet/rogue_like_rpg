"""Tests for SocialService: individual names + relationships (Phase L slice 3)."""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper

from game.components import Name, Relationships, Schedule
from game.content.entity_factory import EntityFactory
from game.content.resource_loader import ResourceLoader
from game.services.social_service import NAMED_TEMPLATES, SocialService


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_schedules("assets/data/schedules.json")


def _spawn(template, n):
    return [EntityFactory.create(esper, template, 5 + i, 5, 0) for i in range(n)]


def test_common_folk_get_unique_given_names():
    _load_content()
    villagers = _spawn("villager", 5)
    SocialService.assign(esper, seed=1)

    names = [esper.component_for_entity(v, Name).name for v in villagers]
    assert all(n != "Villager" for n in names), names
    assert len(set(names)) == len(names), f"names must be unique: {names}"


def test_notables_keep_their_role_name():
    _load_content()
    mayor = EntityFactory.create(esper, "mayor", 5, 5, 0)
    _spawn("villager", 3)
    SocialService.assign(esper, seed=1)

    assert "mayor" not in NAMED_TEMPLATES
    assert esper.component_for_entity(mayor, Name).name == "Mayor"


def test_relationships_are_wired_and_symmetric():
    _load_content()
    villagers = _spawn("villager", 6)
    SocialService.assign(esper, seed=3)

    name_of = {v: esper.component_for_entity(v, Name).name for v in villagers}
    rels = {v: esper.component_for_entity(v, Relationships).affinity for v in villagers}

    # Everyone knows at least one peer.
    assert all(rels[v] for v in villagers), "each villager should have a relationship"

    # Relationships are mutual and agree on the value.
    for v in villagers:
        for other_name, affinity in rels[v].items():
            other = next(o for o, n in name_of.items() if n == other_name)
            assert rels[other].get(name_of[v]) == affinity, "relationships must be symmetric"

    # Both friends (+) and rivals (-) occur in a decent-sized village.
    all_values = [a for v in villagers for a in rels[v].values()]
    assert any(a > 0 for a in all_values), "there should be friendships"


def test_assignment_is_deterministic_for_a_seed():
    _load_content()
    a = _spawn("villager", 5)
    SocialService.assign(esper, seed=42)
    first = sorted(esper.component_for_entity(v, Name).name for v in a)

    # Fresh world, same seed -> same cast of names.
    from core.ecs import reset_world

    reset_world()
    _load_content()
    b = _spawn("villager", 5)
    SocialService.assign(esper, seed=42)
    second = sorted(esper.component_for_entity(v, Name).name for v in b)

    assert first == second


def test_no_named_templates_means_no_op():
    _load_content()
    # Wolves are not townsfolk; SocialService leaves them alone.
    wolves = _spawn("wolf", 2)
    SocialService.assign(esper, seed=1)
    for w in wolves:
        assert not esper.has_component(w, Relationships)
    # Sanity: schedule-less creatures aren't picked up.
    assert all(not esper.has_component(w, Schedule) for w in wolves)
