"""Tests for quests and rumors (ROADMAP Phase E)."""

import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from game.components import Inventory, PlayerTag, Purse, QuestGiver, TemplateId
from game.content.entity_factory import EntityFactory
from game.content.item_factory import ItemFactory
from game.content.resource_loader import ResourceLoader
from game.services.quest_service import QuestService
from game.services.rumor_service import RumorService

QUESTS_FILE = "assets/data/quests.json"


def _load_content():
    ResourceLoader.load_schedules("assets/data/schedules.json")
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_entities("assets/data/entities.json")
    ResourceLoader.load_items("assets/data/items.json")


class _FakeGraph:
    def __init__(self, current="Village"):
        self.current_location_id = current
        self.locations = {}


class _FakeCtx:
    def __init__(self, current="Village"):
        self.world_graph = _FakeGraph(current)
        self.player_entity = None
        self.economy = None
        self.world_chronicle = None
        self.world_clock = None
        self.reputation = None
        self.map_service = None
        self.quests = None


def _service(current="Village") -> tuple[QuestService, _FakeCtx]:
    ctx = _FakeCtx(current)
    service = QuestService(ctx=ctx, rng=random.Random(1))
    service.load_authored(QUESTS_FILE)
    ctx.quests = service
    return service, ctx


# ---------------------------------------------------------------------------
# Authored quest lifecycle
# ---------------------------------------------------------------------------


def test_authored_quests_load_and_offers_filter_by_location():
    service, _ = _service()
    assert len(service.quests) == 13
    assert [q.id for q in service.offers_at("Village")] == ["long_road"]
    assert [q.id for q in service.offers_at("Eastmoor")] == ["taste_of_home"]


def test_accept_and_journal():
    service, _ = _service()
    quest = service.offers_at("Village")[0]
    service.accept(quest)
    assert quest.state == "active"
    assert quest in service.active_quests()
    assert service.offers_at("Village") == []


def test_visit_quest_completes_on_arrival():
    _load_content()
    service, ctx = _service()
    ctx.player_entity = esper.create_entity(PlayerTag(), Purse(gold=0))
    quest = next(q for q in service.quests if q.id == "long_road")
    service.accept(quest)

    service.on_arrival("Brackenfen")
    assert quest.state == "turned_in"
    assert esper.component_for_entity(ctx.player_entity, Purse).gold == quest.reward_gold


def test_deliver_quest_turn_in_consumes_items_and_pays():
    _load_content()
    service, ctx = _service(current="Eastmoor")
    inventory = Inventory()
    ctx.player_entity = esper.create_entity(PlayerTag(), Purse(gold=0), inventory)
    quest = next(q for q in service.quests if q.id == "taste_of_home")
    service.accept(quest)

    # Not enough potions: turn-in refused
    assert service.turn_in(quest) is False

    for _ in range(2):
        inventory.items.append(ItemFactory.create(esper, "health_potion"))
    assert quest in service.turn_in_candidates("Eastmoor")
    assert service.turn_in(quest) is True
    assert quest.state == "turned_in"
    assert esper.component_for_entity(ctx.player_entity, Purse).gold == quest.reward_gold
    assert inventory.items == []


def test_kill_quest_counts_player_kills_at_location():
    _load_content()
    service, ctx = _service(current="Brackenfen")
    ctx.player_entity = esper.create_entity(PlayerTag(), Purse(gold=0))
    quest = next(q for q in service.quests if q.id == "wolf_cull")
    service.accept(quest)

    wolf1 = esper.create_entity(TemplateId("wolf"))
    wolf2 = esper.create_entity(TemplateId("wolf"))
    orc = esper.create_entity(TemplateId("orc"))

    service.on_entity_died(orc, attacker=ctx.player_entity)  # wrong template
    assert quest.progress == 0
    service.on_entity_died(wolf1, attacker=None)  # no attacker
    assert quest.progress == 0
    service.on_entity_died(wolf1, attacker=ctx.player_entity)
    assert quest.progress == 1 and quest.state == "active"
    service.on_entity_died(wolf2, attacker=ctx.player_entity)
    assert quest.state == "completed"

    # Turn in at the giver
    assert service.turn_in(quest) is True
    assert esper.component_for_entity(ctx.player_entity, Purse).gold == quest.reward_gold


def test_kill_progress_ignores_other_locations():
    _load_content()
    service, ctx = _service(current="Village")  # player is NOT at Brackenfen
    ctx.player_entity = esper.create_entity(PlayerTag())
    quest = next(q for q in service.quests if q.id == "wolf_cull")
    service.accept(quest)

    wolf = esper.create_entity(TemplateId("wolf"))
    service.on_entity_died(wolf, attacker=ctx.player_entity)
    assert quest.progress == 0


# ---------------------------------------------------------------------------
# Quest chains: prerequisites gate later stages; turning one in unlocks next
# ---------------------------------------------------------------------------


def test_quest_chain_gates_and_unlocks_stages():
    _load_content()
    service, ctx = _service(current="Brackenfen")
    inventory = Inventory()
    ctx.player_entity = esper.create_entity(PlayerTag(), Purse(gold=0), inventory)

    # Only the first stage is offered; later stages stay hidden until unlocked.
    offered = [q.id for q in service.offers_at("Brackenfen")]
    assert "lifeline_larder" in offered
    assert "lifeline_tuskers" not in offered
    assert "lifeline_word" not in offered
    # A locked stage is also not gossiped about elsewhere.
    assert all(q.id != "lifeline_tuskers" for q in service.open_offers_elsewhere("Village"))

    # Stage 1: deliver 3 bread -> stage 2 (kill) unlocks.
    larder = next(q for q in service.quests if q.id == "lifeline_larder")
    service.accept(larder)
    for _ in range(3):
        inventory.items.append(ItemFactory.create(esper, "bread"))
    assert service.turn_in(larder) is True
    offered = [q.id for q in service.offers_at("Brackenfen")]
    assert "lifeline_tuskers" in offered
    assert "lifeline_word" not in offered

    # Stage 2: cull 2 boar -> stage 3 (visit) unlocks.
    tuskers = next(q for q in service.quests if q.id == "lifeline_tuskers")
    service.accept(tuskers)
    for _ in range(2):
        boar = esper.create_entity(TemplateId("boar"))
        service.on_entity_died(boar, attacker=ctx.player_entity)
    assert tuskers.state == "completed"
    assert service.turn_in(tuskers) is True
    offered = [q.id for q in service.offers_at("Brackenfen")]
    assert "lifeline_word" in offered


def test_chain_serialization_preserves_prerequisites():
    service, ctx = _service()
    data = service.to_dict()
    restored = QuestService(ctx=ctx)
    restored.from_dict(data)
    word = next(q for q in restored.quests if q.id == "lifeline_word")
    assert word.prerequisites == ["lifeline_tuskers"]
    # With nothing turned in, the gated stage is hidden.
    assert restored._prerequisites_met(word) is False


def test_mayor_dialogue_reacts_to_quest_state():
    from game.content.dialogue_service import DialogueService

    svc = DialogueService()
    svc.load("assets/data/dialogues.json")
    ready_pool = svc._dialogues["mayor"]["conditional"][0]["lines"]
    active_pool = svc._dialogues["mayor"]["conditional"][1]["lines"]
    default_pool = svc._dialogues["mayor"]["default"]

    for _ in range(20):
        assert svc.get_line("mayor", {"quest": "ready"}) in ready_pool
        assert svc.get_line("mayor", {"quest": "active"}) in active_pool
        # No quest context -> the mayor falls back to plain smalltalk.
        assert svc.get_line("mayor", {}) in default_pool


# ---------------------------------------------------------------------------
# Generated quests (E2)
# ---------------------------------------------------------------------------


def test_shortage_generates_deliver_quest():
    _load_content()
    from game.services.economy_service import EconomyService

    service, ctx = _service(current="Eastmoor")
    ctx.player_entity = esper.create_entity(PlayerTag())
    economy = EconomyService()
    economy.stocks = {"Eastmoor": {"health_potion": 0.5}}
    economy.rates_per_day = {"Eastmoor": {"health_potion": -3.0}}
    ctx.economy = economy

    service._generate_offers("Eastmoor")
    generated = [q for q in service.quests if q.source == "generated"]
    assert len(generated) == 1
    quest = generated[0]
    assert quest.quest_type == "deliver"
    assert quest.target["item"] == "health_potion"
    assert quest.reward_gold > 0

    # Idempotent: arriving again does not duplicate the request
    service._generate_offers("Eastmoor")
    assert len([q for q in service.quests if q.source == "generated"]) == 1


def test_no_quest_for_produced_or_stocked_goods():
    _load_content()
    from game.services.economy_service import EconomyService

    service, ctx = _service(current="Brackenfen")
    economy = EconomyService()
    economy.stocks = {"Brackenfen": {"health_potion": 14.0, "iron_sword": 1.0}}
    economy.rates_per_day = {"Brackenfen": {"health_potion": 3.0, "iron_sword": -0.5}}
    ctx.economy = economy

    service._generate_offers("Brackenfen")
    generated = [q for q in service.quests if q.source == "generated"]
    # iron_sword: consumed AND scarce -> quest; health_potion: produced -> none
    assert len(generated) == 1
    assert generated[0].target["item"] == "iron_sword"


def test_wolf_event_generates_hunt_quest():
    _load_content()
    from game.services.world_chronicle_service import WorldChronicleService

    service, ctx = _service(current="Brackenfen")

    class _Clock:
        total_ticks = 1000

    chronicle = WorldChronicleService(ctx=ctx)
    chronicle.record("Brackenfen", tick=900, text="Wolves were spotted near Brackenfen.", event_id="wolves_spotted")
    ctx.world_chronicle = chronicle
    ctx.world_clock = _Clock()

    service._generate_offers("Brackenfen")
    hunts = [q for q in service.quests if q.id == "gen_wolves_Brackenfen"]
    assert len(hunts) == 1
    assert hunts[0].quest_type == "kill"
    assert hunts[0].target["template"] == "wolf"


def test_serialization_roundtrip():
    service, ctx = _service()
    quest = service.offers_at("Village")[0]
    service.accept(quest)
    data = service.to_dict()

    restored = QuestService(ctx=ctx)
    restored.from_dict(data)
    assert len(restored.quests) == 13
    assert next(q for q in restored.quests if q.id == quest.id).state == "active"


# ---------------------------------------------------------------------------
# Rumors (E3)
# ---------------------------------------------------------------------------


def test_rumors_point_at_other_locations():
    _load_content()
    from game.services.world_chronicle_service import WorldChronicleService

    service, ctx = _service(current="Village")

    class _Clock:
        total_ticks = 1000

    chronicle = WorldChronicleService(ctx=ctx)
    chronicle.record("Eastmoor", tick=950, text="A brawl broke out in the tavern of Eastmoor.", event_id="tavern_brawl")
    chronicle.record("Village", tick=950, text="Local news.", event_id="feast_day")
    ctx.world_chronicle = chronicle
    ctx.world_clock = _Clock()

    rumors = RumorService(ctx=ctx, rng=random.Random(3))
    candidates = rumors._candidates()
    assert any("Eastmoor" in r for r in candidates)
    assert not any("Local news" in r for r in candidates), "rumors must not repeat local events"
    # Quest offers elsewhere become rumors too
    assert any("taste of home" in r.lower() or "Eastmoor could use help" in r for r in candidates)


def test_maybe_rumor_respects_chance():
    service, ctx = _service(current="Village")
    rumors = RumorService(ctx=ctx, rng=random.Random(0))
    # With no chronicle/quest material beyond offers elsewhere, repeated calls
    # must never raise and must sometimes return None.
    results = {rumors.maybe_rumor() for _ in range(20)}
    assert None in results


# ---------------------------------------------------------------------------
# Phase E done-criterion: rumor -> travel -> resolve a generated quest
# whose cause genuinely exists in the simulation
# ---------------------------------------------------------------------------


def test_rumor_leads_to_generated_quest_with_real_cause():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    ctx = gc.ctx
    ctx.travel_encounters.templates = []  # deterministic direct travel, no road events
    surface = pygame.display.get_surface()

    log: list[str] = []

    def _capture(msg, turn=None, category=None):
        log.append(str(msg))

    esper.set_handler("log_message", _capture)

    def key(k):
        gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))
        if gc.state.done:
            gc.flip_state()

    def frames(n=5):
        for _ in range(n):
            gc.state.update(0.016)
            gc.state.draw(surface)

    frames()

    # The simulation produced a wolf sighting at Brackenfen while the
    # player is in the Village.
    ctx.world_chronicle.record(
        "Brackenfen",
        tick=ctx.world_clock.total_ticks,
        text="Wolves were spotted near Brackenfen.",
        event_id="wolves_spotted",
    )
    ctx.rumors.rng = random.Random(2)

    # 1) Hear about it through smalltalk: bump a villager until the rumor drops
    from game.components import AI, Activity, Position, Schedule

    pos = esper.component_for_entity(ctx.player_entity, Position)
    villager = EntityFactory.create(esper, "villager", pos.x + 1, pos.y, pos.layer)
    # Pin the conversation partner: no wandering off mid-test
    for comp_type in (AI, Schedule, Activity):
        if esper.has_component(villager, comp_type):
            esper.remove_component(villager, comp_type)
    key(pygame.K_RIGHT)  # bump -> opens the conversation window
    frames(2)
    key(pygame.K_RETURN)  # topic "Ask about the roads" -> reveals Brackenfen
    frames(2)
    key(pygame.K_DOWN)  # move to the "Heard any news?" topic
    heard = False
    for _ in range(30):
        log.clear()
        key(pygame.K_RETURN)  # ask for news until the wolf rumor surfaces
        frames(2)
        if any("Brackenfen" in m and "Wolves" in m for m in log):
            heard = True
            break
    assert heard, "a villager should eventually pass on the wolf rumor"
    key(pygame.K_ESCAPE)  # leave the conversation before travelling on
    frames(2)

    # 2) Travel to Brackenfen
    key(pygame.K_m)
    idx = next(i for i, (loc, _) in enumerate(gc.state.destinations) if loc.id == "Brackenfen")
    for _ in range(idx):
        key(pygame.K_DOWN)
    key(pygame.K_RETURN)
    assert ctx.map_service.active_map_id == "Brackenfen"
    frames()

    # 3) The simulation-generated hunt request exists at the giver
    offers = [q for q in ctx.quests.offers_at("Brackenfen") if q.id == "gen_wolves_Brackenfen"]
    assert offers, "arriving at Brackenfen should offer the generated wolf hunt"
    quest = offers[0]
    ctx.quests.accept(quest)

    # 4) The cause genuinely exists — in Brackenfen's wilderness. Take the
    # path into the wilds; entering spawns the missing wolves.
    from game.components import Portal

    wild_portal = next(
        (pos, portal)
        for _e, (pos, portal) in esper.get_components(Position, Portal)
        if portal.target_map_id == "Brackenfen Wilderness"
    )
    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = wild_portal[0].x, wild_portal[0].y
    frames(2)
    key(pygame.K_g)
    frames()
    assert ctx.map_service.active_map_id == "Brackenfen Wilderness"
    assert ctx.world_graph.current_location_id == "Brackenfen", "wilderness is not a world-graph node"

    wolves = [
        ent
        for ent, (tid,) in esper.get_components(TemplateId)
        if tid.id == "wolf" and esper.has_component(ent, Position)
    ]
    assert len(wolves) >= quest.target["count"]

    # 5) Resolve it: hunt the wolves in the wilds, return, collect the reward
    gold_before = esper.component_for_entity(ctx.player_entity, Purse).gold
    for wolf in wolves[: quest.target["count"]]:
        ctx.quests.on_entity_died(wolf, attacker=ctx.player_entity)
    assert quest.state == "completed"

    back_portal = next(
        (pos, portal)
        for _e, (pos, portal) in esper.get_components(Position, Portal)
        if portal.target_map_id == "Brackenfen"
    )
    player_pos = esper.component_for_entity(ctx.player_entity, Position)
    player_pos.x, player_pos.y = back_portal[0].x, back_portal[0].y
    frames(2)
    key(pygame.K_g)
    frames()
    assert ctx.map_service.active_map_id == "Brackenfen", "the return path leads back where you came from"

    assert ctx.quests.turn_in(quest) is True
    assert esper.component_for_entity(ctx.player_entity, Purse).gold == gold_before + quest.reward_gold


# ---------------------------------------------------------------------------
# End-to-end: bump the mayor, accept, journal shows it
# ---------------------------------------------------------------------------


def test_bump_mayor_opens_quest_window_and_accepts():
    from game.ui.windows.quests import QuestWindow

    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    ctx = gc.ctx
    surface = pygame.display.get_surface()
    # Silence rumors for deterministic dialogue flow
    from game.content.content_database import default_content

    default_content.dialogues.rumor_provider = None

    def key(k):
        game.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

    def frames(n=5):
        for _ in range(n):
            game.update(0.016)
            game.draw(surface)

    frames()

    # Place a mayor next to the player and bump into it
    from game.components import Position

    pos = esper.component_for_entity(ctx.player_entity, Position)
    mayor = EntityFactory.create(esper, "mayor", pos.x + 1, pos.y, pos.layer)
    assert esper.has_component(mayor, QuestGiver)
    key(pygame.K_RIGHT)
    frames()

    assert ctx.ui_stack.is_active(), "bumping a quest giver should open the quest window"
    window = ctx.ui_stack.stack[-1]
    assert isinstance(window, QuestWindow)
    offers = ctx.quests.offers_at("Village")
    assert offers, "the Village mayor should offer 'The Long Road'"

    key(pygame.K_RETURN)  # accept
    frames()
    assert offers[0].state == "active"

    key(pygame.K_ESCAPE)
    frames()
    assert not ctx.ui_stack.is_active()

    # Journal shows the active quest
    key(pygame.K_j)
    frames()
    assert ctx.ui_stack.is_active()
    journal = ctx.ui_stack.stack[-1]
    assert isinstance(journal, QuestWindow) and journal.mode == "journal"
    assert journal._entries(), "journal should list the accepted quest"
    key(pygame.K_ESCAPE)
    frames()


# ---------------------------------------------------------------------------
# Guide quests: a friendly settlement advertises a neighbour's need and the
# acceptance reveals the road there (quest-driven location discovery).
# ---------------------------------------------------------------------------


class _FakeEconomy:
    def __init__(self, stocks):
        self.stocks = stocks

    def consumes(self, location_id, item_id):
        return True


def _friends_graph():
    from game.services.world_graph_service import WorldGraphService, WorldLocation

    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="Village", name="Village", discovered=True, friends=["Brackenfen"]))
    graph.add_location(WorldLocation(id="Brackenfen", name="Brackenfen", discovered=False, friends=["Village"]))
    graph.add_route("Village", "Brackenfen", 100)
    graph.start_location_id = "Village"
    graph.current_location_id = "Village"
    return graph


def test_guide_quest_offered_by_friend_and_reveals_route_on_accept():
    _load_content()
    ctx = _FakeCtx()
    ctx.world_graph = _friends_graph()
    ctx.economy = _FakeEconomy({"Brackenfen": {"bread": 0.0}})
    service = QuestService(ctx=ctx, rng=random.Random(1))
    ctx.quests = service

    service._generate_guide_offers("Village")
    guides = [q for q in service.offers_at("Village") if q.id.startswith("gen_guide_")]
    assert guides, "a guide quest should be offered at the friendly settlement"
    quest = guides[0]
    assert quest.where_offered == "Village" and quest.giver_location == "Brackenfen"
    assert quest.quest_type == "deliver" and quest.target["item"] == "bread"

    # The destination is unknown until you take the job.
    assert not ctx.world_graph.get_location("Brackenfen").discovered
    service.accept(quest)
    assert ctx.world_graph.get_location("Brackenfen").discovered, "accepting reveals the road to the friend"


def test_no_guide_quest_without_a_shortage():
    _load_content()
    ctx = _FakeCtx()
    ctx.world_graph = _friends_graph()
    ctx.economy = _FakeEconomy({"Brackenfen": {"bread": 99.0}})  # well stocked
    service = QuestService(ctx=ctx, rng=random.Random(1))
    ctx.quests = service

    service._generate_guide_offers("Village")
    assert not [q for q in service.quests if q.id.startswith("gen_guide_")]


def test_no_guide_quest_to_unconnected_friend():
    _load_content()
    from game.services.world_graph_service import WorldGraphService, WorldLocation

    graph = WorldGraphService()
    graph.add_location(WorldLocation(id="Village", name="Village", discovered=True, friends=["Faraway"]))
    graph.add_location(WorldLocation(id="Faraway", name="Faraway", discovered=False))
    # No route between them — a guide can't point a road that doesn't exist.
    graph.current_location_id = "Village"
    ctx = _FakeCtx()
    ctx.world_graph = graph
    ctx.economy = _FakeEconomy({"Faraway": {"bread": 0.0}})
    service = QuestService(ctx=ctx, rng=random.Random(1))
    ctx.quests = service

    service._generate_guide_offers("Village")
    assert not [q for q in service.quests if q.id.startswith("gen_guide_")]
