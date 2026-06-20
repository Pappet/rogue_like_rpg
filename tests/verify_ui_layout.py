"""UI layout regression guard.

Renders every modal window with worst-case content (every item in items.json,
longest descriptions/names, full lists) and asserts that no drawn text or bar
spills out of the inset box it sits in, or out of the window panel. This is the
automated form of the manual overflow audit; it catches things CI would
otherwise miss, like a detail pane growing a line or a list gaining a row.

A few pixels of tolerance absorb font-metric differences between platforms /
Python versions (the SysFont fallback differs in CI), while still catching the
structural overflows we care about (a spilled row is ~10px+, well above noise).
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import esper
import pygame
import pytest

from config import UI_CRAFT_RECT, UI_MODAL_RECT, UI_REST_RECT
from core.ui import theme
from game.components import (
    Description,
    EffectiveStats,
    Equipment,
    Inventory,
    Merchant,
    Purse,
    Skills,
    Stats,
)
from game.content.item_factory import ItemFactory
from game.content.item_registry import item_registry
from game.content.recipe_registry import recipe_registry
from game.content.resource_loader import ResourceLoader
from game.systems.action_system import ActionSystem

# How far a glyph may poke past its box before we call it an overflow. Real
# overflows are whole rows / lines (10px+); this only forgives sub-pixel and
# font-metric jitter.
TOL_RIGHT = 6
TOL_BOTTOM = 8


class _Capture:
    """Patches the theme draw helpers to record what gets drawn where."""

    def __init__(self):
        self.texts = []  # (text, pygame.Rect)
        self.bars = []  # pygame.Rect
        self.insets = []  # pygame.Rect

    def __enter__(self):
        self._text, self._bar, self._inset = theme.draw_text, theme.draw_bar, theme.draw_inset

        def text(surface, t, font, color, pos, **kw):
            r = self._text(surface, t, font, color, pos, **kw)
            self.texts.append((str(t), pygame.Rect(r)))
            return r

        def bar(surface, rect, *a, **kw):
            self.bars.append(pygame.Rect(rect))
            return self._bar(surface, rect, *a, **kw)

        def inset(surface, rect, *a, **kw):
            self.insets.append(pygame.Rect(rect))
            return self._inset(surface, rect, *a, **kw)

        theme.draw_text, theme.draw_bar, theme.draw_inset = text, bar, inset
        return self

    def __exit__(self, *exc):
        theme.draw_text, theme.draw_bar, theme.draw_inset = self._text, self._bar, self._inset

    def _smallest_inset_at(self, r):
        best = None
        for ins in self.insets:
            if ins.collidepoint(r.x + 1, r.y + 1) and (best is None or ins.w * ins.h < best.w * best.h):
                best = ins
        return best

    def overflows(self, panel):
        """Return a list of human-readable overflow descriptions (empty = OK)."""
        panel = pygame.Rect(panel)
        bad = []
        for label, r in [(t, rr) for t, rr in self.texts] + [("<bar>", rr) for rr in self.bars]:
            box = self._smallest_inset_at(r) or panel
            if r.right - (box.right - 3) > TOL_RIGHT or r.bottom - (box.bottom - 1) > TOL_BOTTOM:
                bad.append(f"{label!r} rect={tuple(r)} escapes box={tuple(box)}")
            # Everything must also stay inside the window panel itself.
            if r.right - panel.right > TOL_RIGHT or r.bottom - panel.bottom > TOL_BOTTOM:
                bad.append(f"{label!r} rect={tuple(r)} escapes panel={tuple(panel)}")
        return bad


def _load_content():
    ResourceLoader.load_tiles("assets/data/tile_types.json")
    ResourceLoader.load_items("assets/data/items.json")
    ResourceLoader.load_recipes("assets/data/recipes.json")


def _full_player():
    """Player carrying one of every item, with skills trained — worst case for
    the inventory / character panes."""
    stats = Stats(
        hp=10, max_hp=10, power=3, defense=2, mana=5, max_mana=5, perception=5, intelligence=5, max_carry_weight=8.0
    )
    eff = EffectiveStats(hp=10, max_hp=10, power=3, defense=2, mana=5, max_mana=5, perception=5, intelligence=5)
    inv = Inventory()
    skills = Skills()
    player = esper.create_entity(inv, stats, eff, Purse(gold=123456), Equipment(), skills)
    for tid in item_registry.all_ids():
        ent = ItemFactory.create(esper, tid)
        if ent is not None:
            inv.items.append(ent)
    return player, inv


def _select_longest_detail(window, items):
    longest = -1
    for i, it in enumerate(items):
        length = len(ActionSystem.get_detailed_description(esper, it))
        if length > longest:
            longest, window.selected_idx = length, i


@pytest.fixture
def surface():
    pygame.font.init()
    return pygame.Surface((1280, 720))


def _assert_clean(name, cap, panel):
    bad = cap.overflows(panel)
    assert not bad, f"{name} layout overflow:\n  " + "\n  ".join(bad)


def test_inventory_window_no_overflow(surface):
    _load_content()
    player, inv = _full_player()
    from game.ui.windows.inventory import InventoryWindow

    window = InventoryWindow(pygame.Rect(*UI_MODAL_RECT), player, MagicMock(), MagicMock())
    _select_longest_detail(window, inv.items)
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean("Inventory", cap, UI_MODAL_RECT)


def test_pickup_window_no_overflow(surface):
    _load_content()
    player, inv = _full_player()
    from game.services.player_action_service import PlayerActionService
    from game.ui.windows.pickup import PickupWindow

    actions = PlayerActionService(
        SimpleNamespace(player_entity=player, systems=SimpleNamespace(turn_system=MagicMock()))
    )
    window = PickupWindow(pygame.Rect(*UI_MODAL_RECT), inv.items[:], actions, MagicMock())
    _select_longest_detail(window, inv.items)
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean("Pickup", cap, UI_MODAL_RECT)


def test_character_window_no_overflow(surface):
    _load_content()
    player, _inv = _full_player()
    from game.services.skill_service import SKILLS
    from game.ui.windows.character import CharacterWindow

    skills = esper.component_for_entity(player, Skills)
    for sid in SKILLS:
        skills.xp[sid] = 500
    window = CharacterWindow(pygame.Rect(*UI_MODAL_RECT), player, MagicMock())
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean("Character", cap, UI_MODAL_RECT)


def test_tooltip_window_no_overflow(surface):
    _load_content()
    player, inv = _full_player()
    from game.ui.windows.tooltip import TooltipWindow

    worst, longest = inv.items[0], -1
    for it in inv.items:
        desc = esper.try_component(it, Description)
        if desc and len(desc.get(None)) > longest:
            longest, worst = len(desc.get(None)), it
    window = TooltipWindow(pygame.Rect(900, 80, 320, 260), [worst])
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean("Tooltip", cap, (900, 80, 320, 260))


@pytest.mark.parametrize("pane", [0, 1])
def test_trade_window_no_overflow(surface, pane):
    _load_content()
    player, _inv = _full_player()
    from game.ui.windows.trade import TradeWindow

    ids = item_registry.all_ids()
    merchant = esper.create_entity(Merchant(stock=ids[:], base_stock=ids[:]), Purse(gold=999))
    ctx = SimpleNamespace(input_manager=MagicMock(), economy=None, reputation=None, world_graph=None)
    window = TradeWindow(pygame.Rect(*UI_MODAL_RECT), player, merchant, ctx)
    window.active_pane = pane
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean(f"Trade pane {pane}", cap, UI_MODAL_RECT)


def test_crafting_window_no_overflow(surface):
    _load_content()
    player, _inv = _full_player()
    from game.ui.windows.crafting import CraftWindow

    station = recipe_registry.get(recipe_registry.all_ids()[0]).station
    ctx = SimpleNamespace(input_manager=MagicMock(), economy=None, reputation=None, world_graph=None)
    window = CraftWindow(pygame.Rect(*UI_CRAFT_RECT), player, station, ctx, lambda r: None)
    # Highlight the recipe whose output carries the longest description.
    longest = -1
    for i, recipe in enumerate(window.recipes):
        tpl = item_registry.get(recipe.output)
        length = len(tpl.description) if tpl and tpl.description else 0
        if length > longest:
            longest, window.selected_idx = length, i
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean("Crafting", cap, UI_CRAFT_RECT)


@pytest.mark.parametrize("mode", ["giver", "journal"])
def test_quest_window_no_overflow(surface, mode):
    _load_content()
    from game.ui.windows.quests import QuestWindow

    long_title = "The Exceedingly Long and Winding Quest of the Forgotten Mountain Kings"
    long_desc = "Travel across the whole realm to deliver this very long parcel to a distant cousin far away."

    def quest(kind_type, gold):
        return SimpleNamespace(
            title=long_title,
            description=long_desc,
            reward_gold=gold,
            quest_type=kind_type,
            target={"count": 7},
            progress=3,
            state="active",
            giver_location="Brackenfen",
        )

    quests = SimpleNamespace(
        active_quests=lambda: [quest("kill", 500) for _ in range(6)],
        turn_in_candidates=lambda loc: [quest("deliver", 250) for _ in range(3)],
        offers_at=lambda loc: [quest("deliver", 99) for _ in range(4)],
    )
    ctx = SimpleNamespace(
        input_manager=MagicMock(),
        world_graph=SimpleNamespace(current_location_id="Brackenfen"),
        quests=quests,
    )
    window = QuestWindow(pygame.Rect(*UI_MODAL_RECT), ctx, mode=mode)
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean(f"Quests {mode}", cap, UI_MODAL_RECT)


def test_rest_window_no_overflow(surface):
    from game.ui.windows.rest import RestWindow

    options = [
        ("Short nap", 60),
        ("Sleep until dawn", 480),
        ("Wait a moment", 10),
        ("Long rest", 600),
        ("Extra option A", 120),
        ("Extra option B", 240),
        ("Extra option C", 300),
        ("Extra option D", 360),
    ]
    window = RestWindow(pygame.Rect(*UI_REST_RECT), "Rest", options, MagicMock(), lambda *a: None)
    with _Capture() as cap:
        window.draw(surface)
    _assert_clean("Rest", cap, UI_REST_RECT)
