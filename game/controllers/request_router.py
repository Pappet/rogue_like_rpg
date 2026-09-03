"""Routes ``*_requested`` events to the windows that answer them.

A lower layer asks for something it must not know how to do: MovementSystem
bumping a forge dispatches ``craft_requested``, not "open a CraftWindow".
GameplayState is the layer allowed to answer, and until now every answer
repeated the same three lines — bail out if a modal is already up, build the
rect, push the window. Collecting that here makes a new request one
registration instead of another near-identical handler method.

Two esper details make subscription lifetime the tricky part, and the router
exists partly to hold them in one place:

1. ``esper.set_handler`` keeps only a *weak* reference. A closure registered
   and then dropped is collected, and the event silently stops arriving — so
   the router keeps every handler it registers alive.
2. ``esper.remove_handler`` looks a handler up as ``weakref.ref(func)`` while
   ``set_handler`` stores a ``WeakMethod`` for bound methods, so it cannot
   remove a method handler at all. Wrapping every registration in a plain
   closure the router owns makes unsubscribing work.

Point 1 is what makes ``clear()`` mandatory rather than tidy. Handler lifetime
used to take care of itself: a handler bound to an object rebuilt on each
``startup()`` died with that object. Now the router keeps handlers alive, so a
state that re-registers without clearing leaves the previous generation
subscribed and *both* fire — which is how this router first shipped a bug,
charging double travel time because the map transition ran twice.

(Dropping the router's own reference is what actually unsubscribes, since
esper's weakref callback then prunes the entry. ``clear()`` calls
``remove_handler`` as well so the unsubscribe is immediate and explicit rather
than a consequence of refcounting.)
"""

from collections.abc import Callable, Sequence
from typing import Any

import esper
import pygame

from config.enums import GameEvent
from core.ui.stack_manager import UIStack
from core.ui.window_base import UIWindow

WindowFactory = Callable[[pygame.Rect, Any], UIWindow]


class RequestRouter:
    """Subscribes a state's answers to the requests dispatched at it."""

    def __init__(self, ui_stack: UIStack) -> None:
        self._ui_stack = ui_stack
        # Strong references: esper's registry holds weak ones only.
        self._subscriptions: list[tuple[GameEvent, Callable[..., Any]]] = []

    def on(self, event: GameEvent, handler: Callable[..., Any]) -> None:
        """Answer ``event`` by calling ``handler`` with the dispatched payload."""

        def invoke(*args: Any) -> None:
            handler(*args)

        self._subscriptions.append((event, invoke))
        esper.set_handler(event, invoke)

    def clear(self) -> None:
        """Unsubscribe everything this router registered.

        Call it before re-registering (a state re-entered), otherwise the old
        subscriptions keep firing alongside the new ones.
        """
        for event, handler in self._subscriptions:
            esper.remove_handler(event, handler)
        self._subscriptions.clear()

    def modal(self, event: GameEvent, rect: Sequence[int], factory: WindowFactory) -> None:
        """Answer ``event`` by opening the window ``factory`` builds.

        Does nothing while another modal is open, so a bump cannot stack a
        second window on top of the one the player is reading.
        """
        bounds = tuple(rect)

        def open_window(payload: Any = None) -> None:
            if self._ui_stack.is_active():
                return
            self._ui_stack.push(factory(pygame.Rect(*bounds), payload))

        self.on(event, open_window)
