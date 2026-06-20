"""Tests for WorldGraphService (ROADMAP Phase A: world skeleton)."""

import pytest

from game.services.world_graph_service import WorldGraphService, WorldLocation

WORLD_FILE = "assets/data/world.json"


def _small_graph() -> WorldGraphService:
    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="A", name="Alpha", discovered=True))
    graph.add_location(WorldLocation(id="B", name="Beta", discovered=True))
    graph.add_location(WorldLocation(id="C", name="Gamma", discovered=False))
    graph.add_route("A", "B", 100)
    graph.add_route("B", "C", 50)
    graph.start_location_id = "A"
    graph.current_location_id = "A"
    return graph


class TestConstruction:
    def test_duplicate_location_rejected(self):
        graph = _small_graph()
        with pytest.raises(ValueError):
            graph.add_location(WorldLocation(id="A", name="Duplicate"))

    def test_route_to_unknown_location_rejected(self):
        graph = _small_graph()
        with pytest.raises(ValueError):
            graph.add_route("A", "Nowhere", 10)

    def test_route_needs_positive_ticks(self):
        graph = _small_graph()
        with pytest.raises(ValueError):
            graph.add_route("A", "C", 0)


class TestQueries:
    def test_neighbors_are_symmetric(self):
        graph = _small_graph()
        assert [loc.id for loc, _ in graph.neighbors("A")] == ["B"]
        assert sorted(loc.id for loc, _ in graph.neighbors("B")) == ["A", "C"]

    def test_travel_ticks_for_route_and_missing_route(self):
        graph = _small_graph()
        assert graph.travel_ticks("A", "B") == 100
        assert graph.travel_ticks("B", "A") == 100
        assert graph.travel_ticks("A", "C") is None

    def test_discovered_neighbors_hides_unknown_locations(self):
        graph = _small_graph()
        assert [loc.id for loc, _ in graph.discovered_neighbors("B")] == ["A"]
        graph.discover("C")
        assert sorted(loc.id for loc, _ in graph.discovered_neighbors("B")) == ["A", "C"]


class TestStateChanges:
    def test_set_current_location(self):
        graph = _small_graph()
        graph.set_current_location("B")
        assert graph.current_location_id == "B"

    def test_set_current_location_unknown_raises(self):
        graph = _small_graph()
        with pytest.raises(ValueError):
            graph.set_current_location("Nowhere")

    def test_discover_is_idempotent(self):
        graph = _small_graph()
        graph.discover("C")
        graph.discover("C")
        assert graph.get_location("C").discovered is True

    def test_discover_implies_heard(self):
        graph = _small_graph()
        graph.discover("C")
        assert graph.get_location("C").heard is True

    def test_hear_is_a_lead_not_a_route(self):
        graph = _small_graph()
        assert graph.hear("C") is True
        c = graph.get_location("C")
        assert c.heard and not c.discovered
        assert graph.hear("C") is False, "already heard"
        assert [loc.id for loc, _ in graph.discovered_neighbors("B")] == ["A"], "heard != travelable"
        assert [loc.id for loc in graph.heard_undiscovered()] == ["C"]


class TestRevealRoutes:
    """Wegauskunft: locals reveal the roads out of the current town."""

    def test_reveal_discovers_neighbouring_settlements(self):
        graph = _small_graph()
        graph.get_location("C").type = "settlement"
        newly = graph.reveal_routes_from("B")
        assert [loc.id for loc in newly] == ["C"]
        assert graph.get_location("C").discovered

    def test_reveal_gates_pois_until_heard(self):
        graph = _small_graph()
        graph.get_location("C").type = "poi"
        # An unheard POI stays secret even when adjacent and asked about.
        assert graph.reveal_routes_from("B") == []
        assert not graph.get_location("C").discovered
        # Once heard (a rumor), directions reveal the route to it.
        graph.hear("C")
        newly = graph.reveal_routes_from("B")
        assert [loc.id for loc in newly] == ["C"]
        assert graph.get_location("C").discovered

    def test_reveal_is_idempotent_when_nothing_new(self):
        graph = _small_graph()  # A,B discovered; C is a POI-less settlement neighbour of B
        graph.reveal_routes_from("B")
        assert graph.reveal_routes_from("B") == []


class TestWorldJson:
    def test_world_file_loads(self):
        graph = WorldGraphService.from_file(WORLD_FILE)
        assert graph.start_location_id is not None
        assert graph.current_location_id == graph.start_location_id
        assert graph.start_location_id in graph.locations
        assert len(graph.locations) >= 2
        assert len(graph.routes) >= 1

    def test_start_location_starts_isolated_until_directions(self):
        """New game: the player knows only the start town. Asking locals for
        directions (reveal_routes_from) is what puts neighbours on the map."""
        graph = WorldGraphService.from_file(WORLD_FILE)
        start = graph.start_location_id
        assert graph.neighbors(start), "the start location must have at least one route"
        assert not graph.discovered_neighbors(start), "no destinations are known before asking around"
        newly = graph.reveal_routes_from(start)
        assert newly, "asking locals must reveal the roads out of the start town"
        assert graph.discovered_neighbors(start), "directions make neighbouring settlements travelable"

    def test_all_routes_reference_known_locations(self):
        graph = WorldGraphService.from_file(WORLD_FILE)
        for route in graph.routes:
            assert route.a in graph.locations
            assert route.b in graph.locations
