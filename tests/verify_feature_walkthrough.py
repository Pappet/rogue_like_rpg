"""End-to-end feature walkthrough: plays the real game headlessly.

Boots the full GameController (like verify_game_loop_smoke) and exercises the
player-facing features through real key events: item pickup, equip/unequip,
consumables, NPC dialogue via bump, combat with death + loot, portal map
transitions, UI windows and a multi-turn stability run.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from config import GameStates
from game.components import (
    AI,
    EffectiveStats,
    Equipment,
    Inventory,
    Portable,
    Portal,
    Position,
    Stats,
)
from game.content.entity_factory import EntityFactory
from game.content.item_factory import ItemFactory
from game.services import equipment_service
from game.services.consumable_service import ConsumableService

# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _Harness:
    """Boots the game and offers key/frame helpers plus a log capture."""

    def __init__(self):
        pygame.init()
        pygame.display.set_mode((1280, 720))
        from main import GameController

        self.gc = GameController()
        self.game = self.gc.states["GAME"]
        self.game.startup(self.gc.ctx)
        self.ctx = self.gc.ctx
        self.player = self.ctx.player_entity
        self.log: list[str] = []
        esper.set_handler("log_message", self._capture_log)

    def _capture_log(self, msg, turn=None, category=None):
        self.log.append(str(msg))

    def frames(self, n: int = 5, dt: float = 0.016):
        surface = pygame.display.get_surface()
        for _ in range(n):
            self.game.update(dt)
            self.game.draw(surface)

    def key(self, k):
        self.game.get_event(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))

    def player_pos(self) -> Position:
        return esper.component_for_entity(self.player, Position)

    def find_open_spot(self):
        """A walkable tile whose four neighbours are walkable and entity-free."""
        mc = self.ctx.map_container
        layer_idx = self.player_pos().layer
        occupied = {(p.x, p.y) for _, (p,) in esper.get_components(Position)}
        for y in range(2, mc.height - 2):
            for x in range(2, mc.width - 2):
                cells = [(x, y), (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
                if all(mc.is_walkable(cx, cy, layer_idx) for cx, cy in cells) and all(c not in occupied for c in cells):
                    return x, y
        raise AssertionError("no open spot found on active map")

    def teleport_to_open_spot(self):
        x, y = self.find_open_spot()
        pos = self.player_pos()
        pos.x, pos.y = x, y
        self.frames(2)
        return x, y


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_pickup_equip_unequip():
    h = _Harness()
    h.teleport_to_open_spot()

    inv = esper.component_for_entity(h.player, Inventory)
    pos = h.player_pos()
    sword = ItemFactory.create_on_ground(esper, "iron_sword", pos.x, pos.y, pos.layer)

    h.key(pygame.K_g)  # interact -> pickup
    h.frames()
    assert sword in inv.items, "sword should be in inventory after pickup"
    assert not esper.has_component(sword, Position), "picked-up item must lose Position"

    base_power = esper.component_for_entity(h.player, EffectiveStats).power
    equipment_service.equip_item(esper, h.player, sword)
    h.frames(2)  # EquipmentSystem recomputes EffectiveStats
    assert esper.component_for_entity(h.player, EffectiveStats).power == base_power + 5
    assert sword in esper.component_for_entity(h.player, Equipment).slots.values()

    equipment_service.equip_item(esper, h.player, sword)  # toggle = unequip
    h.frames(2)
    assert esper.component_for_entity(h.player, EffectiveStats).power == base_power


def test_consumable_heals_and_is_consumed():
    h = _Harness()
    inv = esper.component_for_entity(h.player, Inventory)
    stats = esper.component_for_entity(h.player, Stats)

    potion = ItemFactory.create(esper, "health_potion")
    inv.items.append(potion)
    stats.hp = max(1, stats.hp - 6)
    h.frames(2)

    hp_before = stats.hp
    assert ConsumableService.use_item(esper, h.player, potion) is True
    assert stats.hp == hp_before + 6
    assert not esper.entity_exists(potion)
    assert potion not in inv.items

    # At full health a second potion is refused and kept
    potion2 = ItemFactory.create(esper, "health_potion")
    inv.items.append(potion2)
    assert ConsumableService.use_item(esper, h.player, potion2) is False
    assert esper.entity_exists(potion2)


def test_bump_friendly_npc_talks():
    h = _Harness()
    x, y = h.teleport_to_open_spot()
    villager = EntityFactory.create(esper, "villager", x + 1, y, h.player_pos().layer)
    hp_before = esper.component_for_entity(villager, Stats).hp

    h.log.clear()
    h.key(pygame.K_RIGHT)  # bump
    h.frames()

    assert any("[color=yellow]" in m for m in h.log), f"expected dialogue line, log: {h.log}"
    assert esper.component_for_entity(villager, Stats).hp == hp_before, "talking must not damage the NPC"
    assert (h.player_pos().x, h.player_pos().y) == (x, y), "player must not move into the NPC"


def test_bump_hostile_npc_fights_to_death_with_loot():
    h = _Harness()
    x, y = h.teleport_to_open_spot()
    orc = EntityFactory.create(esper, "orc", x + 1, y, h.player_pos().layer)

    for _ in range(20):
        if not esper.entity_exists(orc) or not esper.has_component(orc, AI):
            break
        h.key(pygame.K_RIGHT)
        h.frames()
    else:
        raise AssertionError("orc did not die within 20 bump attacks")

    loot_here = [ent for ent, (pos, _) in esper.get_components(Position, Portable) if (pos.x, pos.y) == (x + 1, y)]
    assert loot_here, "orc loot table (chance 1.0) should drop items at the death position"


def test_portal_roundtrip():
    h = _Harness()
    # Outbound: any portal leading away from the Village (a structure door,
    # not stairs — stairs target the same map).
    portals = [
        (ent, pos) for ent, (pos, portal) in esper.get_components(Position, Portal) if portal.target_map_id != "Village"
    ]
    assert portals, "Village should contain portals into structures"

    _, p_pos = portals[0]
    pos = h.player_pos()
    pos.x, pos.y = p_pos.x, p_pos.y
    h.frames(2)
    h.key(pygame.K_g)  # interact -> enter portal
    h.frames()
    assert h.ctx.map_service.active_map_id != "Village", "portal should switch the active map"

    # Return: explicitly the portal that targets the Village (not the stairs).
    back = [
        (ent, pos) for ent, (pos, portal) in esper.get_components(Position, Portal) if portal.target_map_id == "Village"
    ]
    assert back, "interior map should contain a return portal to the Village"
    _, b_pos = back[0]
    pos = h.player_pos()
    pos.x, pos.y = b_pos.x, b_pos.y
    h.frames(2)
    h.key(pygame.K_g)
    h.frames()
    assert h.ctx.map_service.active_map_id == "Village", "return portal should lead back to the Village"


def test_ui_windows_open_and_close():
    h = _Harness()
    h.frames()

    h.key(pygame.K_i)
    h.frames()
    assert h.ctx.ui_stack.is_active()
    assert type(h.ctx.ui_stack.stack[-1]).__name__ == "InventoryWindow"
    h.key(pygame.K_ESCAPE)
    h.frames()
    assert not h.ctx.ui_stack.is_active()

    h.key(pygame.K_c)
    h.frames()
    assert type(h.ctx.ui_stack.stack[-1]).__name__ == "CharacterWindow"
    h.key(pygame.K_ESCAPE)
    h.frames()
    assert not h.ctx.ui_stack.is_active()

    h.key(pygame.K_x)
    h.frames()
    assert h.game.turn_system.current_state == GameStates.EXAMINE
    h.key(pygame.K_ESCAPE)
    h.frames()
    assert h.game.turn_system.current_state == GameStates.PLAYER_TURN


def test_multi_turn_stability():
    h = _Harness()
    h.teleport_to_open_spot()

    # This test checks turn-loop stability, not survival: randomly spawned
    # hostiles may otherwise wander over and kill the waiting player
    # (RNG-dependent => flaky). Remove them up front.
    from game.components import AIBehaviorState, Alignment

    hostiles = [
        ent for ent, (behavior,) in esper.get_components(AIBehaviorState) if behavior.alignment == Alignment.HOSTILE
    ]
    for ent in hostiles:
        esper.delete_entity(ent, immediate=True)

    ticks0 = h.ctx.world_clock.total_ticks

    for _ in range(50):
        h.key(pygame.K_SPACE)  # wait
        h.frames(3)

    assert h.ctx.world_clock.total_ticks == ticks0 + 50
    assert h.game.turn_system.current_state == GameStates.PLAYER_TURN
    assert esper.component_for_entity(h.player, Stats).hp > 0
