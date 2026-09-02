"""RequestRouter: subscription lifetime and modal-opening rules.

The router exists to hold two esper quirks in one place — handlers are kept
only weakly, and remove_handler cannot remove a bound method — so these tests
pin exactly those, plus the "one modal at a time" rule.
"""

import gc
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import esper
import pygame

from core.ui.stack_manager import UIStack
from core.ui.window_base import UIWindow
from game.controllers.request_router import RequestRouter

RECT = (10, 10, 100, 80)


class _Window(UIWindow):
    def __init__(self, rect, payload=None):
        super().__init__(rect)
        self.payload = payload


class _Collaborator:
    """Stands in for a service rebuilt on every state startup."""

    def __init__(self):
        self.calls = []

    def handle(self, payload):
        self.calls.append(payload)


# ---------------------------------------------------------------------------
# Plain handlers
# ---------------------------------------------------------------------------


def test_handler_survives_garbage_collection():
    """esper keeps only a weak reference — the router must hold a strong one."""
    router = RequestRouter(UIStack())
    collaborator = _Collaborator()
    router.on("thing_requested", collaborator.handle)

    gc.collect()
    esper.dispatch_event("thing_requested", "payload")

    assert collaborator.calls == ["payload"]


def test_clear_unsubscribes():
    router = RequestRouter(UIStack())
    collaborator = _Collaborator()
    router.on("thing_requested", collaborator.handle)

    router.clear()
    esper.dispatch_event("thing_requested", "payload")

    assert collaborator.calls == []


def test_second_generation_of_handlers_replaces_the_first():
    """The regression this router first shipped with.

    Re-entering gameplay rebuilds its collaborators and registers them again.
    Because the router holds its handlers alive on purpose, skipping clear()
    leaves the previous generation subscribed and *both* fire — which showed up
    as a map transition running twice and charging double travel time.
    """
    router = RequestRouter(UIStack())
    first = _Collaborator()
    router.on("thing_requested", first.handle)

    # State re-entered: collaborators rebuilt, old subscriptions dropped.
    router.clear()
    second = _Collaborator()
    router.on("thing_requested", second.handle)

    esper.dispatch_event("thing_requested", "payload")

    assert first.calls == [], "the previous generation of handlers is still subscribed"
    assert second.calls == ["payload"]


def test_modal_from_a_cleared_router_no_longer_opens_windows():
    stack = UIStack()
    router = RequestRouter(stack)
    router.modal("window_requested", RECT, _Window)

    router.clear()
    esper.dispatch_event("window_requested", "cargo")

    assert stack.stack == []


# ---------------------------------------------------------------------------
# Modal windows
# ---------------------------------------------------------------------------


def test_modal_opens_the_window_the_factory_builds():
    stack = UIStack()
    router = RequestRouter(stack)
    router.modal("window_requested", RECT, _Window)

    esper.dispatch_event("window_requested", "cargo")

    assert len(stack.stack) == 1
    window = stack.stack[-1]
    assert window.payload == "cargo"
    assert window.rect == pygame.Rect(*RECT)


def test_modal_does_not_stack_on_an_open_window():
    """A bump must not push a second window over the one being read."""
    stack = UIStack()
    router = RequestRouter(stack)
    router.modal("window_requested", RECT, _Window)

    esper.dispatch_event("window_requested", "first")
    esper.dispatch_event("window_requested", "second")

    assert len(stack.stack) == 1
    assert stack.stack[-1].payload == "first"
