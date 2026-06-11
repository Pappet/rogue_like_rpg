"""Save/Load tests (ROADMAP Phase A4).

Part 1: component (de)serialization roundtrips.
Part 2: end-to-end snapshot save/load through the real game.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from game.components import (
    Action,
    ActionList,
    Activity,
    AIBehaviorState,
    AIState,
    Alignment,
    Equipment,
    Inventory,
    Name,
    Position,
    Renderable,
    SlotType,
    Stats,
)
from game.services.save_serialization import decode_dataclass, encode_dataclass
from game.services.save_service import SaveService

# ---------------------------------------------------------------------------
# Part 1: serialization roundtrips
# ---------------------------------------------------------------------------


def _roundtrip(component):
    return decode_dataclass(encode_dataclass(component))


def test_roundtrip_simple_components():
    assert _roundtrip(Position(3, 7, 1)) == Position(3, 7, 1)
    assert _roundtrip(Name("Orc")) == Name("Orc")


def test_roundtrip_renderable_restores_color_tuple():
    rend = _roundtrip(Renderable("@", 5, (10, 20, 30)))
    assert rend.color == (10, 20, 30)
    assert isinstance(rend.color, tuple)


def test_roundtrip_enums():
    behavior = _roundtrip(AIBehaviorState(AIState.SLEEP, Alignment.FRIENDLY))
    assert behavior.state is AIState.SLEEP
    assert behavior.alignment is Alignment.FRIENDLY


def test_roundtrip_equipment_enum_keyed_dict():
    eq = Equipment()
    eq.slots[SlotType.MAIN_HAND] = 42
    restored = _roundtrip(eq)
    assert restored.slots[SlotType.MAIN_HAND] == 42
    assert restored.slots[SlotType.HEAD] is None
    assert all(isinstance(k, SlotType) for k in restored.slots)


def test_roundtrip_nested_actions():
    al = ActionList(actions=[Action("Move"), Action("Shoot", range=5, requires_targeting=True)])
    restored = _roundtrip(al)
    assert restored.actions[1].name == "Shoot"
    assert restored.actions[1].range == 5
    assert restored.actions[1].requires_targeting is True


def test_roundtrip_optional_tuple_fields():
    act = Activity(current_activity="WORK", target_pos=(15, 15), home_pos=None)
    restored = _roundtrip(act)
    assert restored.target_pos == (15, 15)
    assert isinstance(restored.target_pos, tuple)
    assert restored.home_pos is None


# ---------------------------------------------------------------------------
# Part 2: end-to-end save/load
# ---------------------------------------------------------------------------


def _boot():
    pygame.init()
    pygame.display.set_mode((1280, 720))
    from main import GameController

    gc = GameController()
    game = gc.states["GAME"]
    gc.state_name = "GAME"
    gc.state = game
    game.startup(gc.ctx)
    return gc, game


def _frames(gc, n=5, dt=0.016):
    surface = pygame.display.get_surface()
    for _ in range(n):
        gc.state.update(dt)
        gc.state.draw(surface)


def _key(gc, key):
    gc.state.get_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=""))
    if gc.state.done:
        gc.flip_state()


def test_save_load_within_session(tmp_path):
    save_file = str(tmp_path / "save.json")
    gc, game = _boot()
    _frames(gc)
    ctx = gc.ctx

    # Build distinctive state: pick up an item, move, advance the clock
    from game.content.item_factory import ItemFactory

    pos = esper.component_for_entity(ctx.player_entity, Position)
    sword = ItemFactory.create_on_ground(esper, "iron_sword", pos.x, pos.y, pos.layer)
    _key(gc, pygame.K_g)
    _frames(gc)
    inv = esper.component_for_entity(ctx.player_entity, Inventory)
    assert sword in inv.items

    for _ in range(5):
        _key(gc, pygame.K_SPACE)
        _frames(gc, 3)

    saved_ticks = ctx.world_clock.total_ticks
    saved_pos = (pos.x, pos.y)
    saved_hp = esper.component_for_entity(ctx.player_entity, Stats).hp
    assert SaveService.save(ctx, save_file) is True

    # Mutate the session afterwards
    for _ in range(10):
        _key(gc, pygame.K_SPACE)
        _frames(gc, 3)
    esper.component_for_entity(ctx.player_entity, Stats).hp = 1

    # Load: state must match the snapshot again
    assert SaveService.load(ctx, save_file) is True
    game.startup(ctx)  # what InputController does after a load
    _frames(gc)

    assert ctx.world_clock.total_ticks == saved_ticks
    new_pos = esper.component_for_entity(ctx.player_entity, Position)
    assert (new_pos.x, new_pos.y) == saved_pos
    assert esper.component_for_entity(ctx.player_entity, Stats).hp == saved_hp

    # Inventory survived with remapped entity ids
    inv = esper.component_for_entity(ctx.player_entity, Inventory)
    assert len(inv.items) == 1
    item = inv.items[0]
    assert esper.component_for_entity(item, Name).name == "Iron Sword"

    # Game continues to run after loading
    _key(gc, pygame.K_SPACE)
    _frames(gc)


def test_save_load_across_boot_preserves_travel(tmp_path):
    save_file = str(tmp_path / "save.json")

    # Session 1: travel to a neighbor settlement, then save
    gc, game = _boot()
    _frames(gc)
    ctx = gc.ctx
    _key(gc, pygame.K_m)
    destination, _ = gc.state.destinations[gc.state.selected_idx]
    _key(gc, pygame.K_RETURN)
    assert ctx.map_service.active_map_id == destination.id
    saved_ticks = ctx.world_clock.total_ticks
    assert SaveService.save(ctx, save_file) is True

    # Session 2: fresh boot (fresh world at Village), then load
    from core.ecs import reset_world
    from game.content.content_database import default_content

    reset_world()
    default_content.clear_all()
    gc2, game2 = _boot()
    ctx2 = gc2.ctx
    assert ctx2.map_service.active_map_id == "Village"

    assert SaveService.load(ctx2, save_file) is True
    game2.startup(ctx2)
    _frames(gc2)

    assert ctx2.map_service.active_map_id == destination.id
    assert ctx2.world_graph.current_location_id == destination.id
    assert ctx2.world_clock.total_ticks == saved_ticks

    # Player exists at the destination's arrival position
    pos = esper.component_for_entity(ctx2.player_entity, Position)
    container = ctx2.map_service.get_map(destination.id)
    assert (pos.x, pos.y) == container.arrival_pos

    # The destination map has live NPCs again and play continues
    _key(gc2, pygame.K_SPACE)
    _frames(gc2)


def test_load_without_file_returns_false(tmp_path):
    gc, _ = _boot()
    assert SaveService.load(gc.ctx, str(tmp_path / "missing.json")) is False


def test_f9_f10_route_to_save_service(monkeypatch):
    calls = []
    monkeypatch.setattr(SaveService, "save", staticmethod(lambda ctx: calls.append("save")))
    monkeypatch.setattr(SaveService, "load", staticmethod(lambda ctx: calls.append("load") or False))

    gc, _ = _boot()
    _frames(gc)
    _key(gc, pygame.K_F9)
    _key(gc, pygame.K_F10)
    assert calls == ["save", "load"]
