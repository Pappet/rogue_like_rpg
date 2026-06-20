"""DialogueWindow + message-log persistence.

Covers the windowed NPC conversation (topic selection -> reply in the
transcript, roads/news routed to RumorService and mirrored to the log) and the
fix that keeps the chronicle's history from resetting when gameplay is
re-entered (UISystem reuses the persisted MessageLog).
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import esper
import pygame

from core.ui.message_log import MessageLog
from game.components import Activity, Name, Renderable, TemplateId
from game.ui.windows.dialogue import DialogueWindow


def _npc():
    return esper.create_entity(
        Name("Aldric"),
        Renderable("v", 5, (200, 180, 120)),
        TemplateId("villager"),
        Activity("WORK"),
    )


def _ctx(directions=None, news=None):
    rumors = SimpleNamespace(directions=lambda: directions, ask_news=lambda: news)
    return SimpleNamespace(input_manager=MagicMock(), rumors=rumors)


def test_window_opens_with_greeting_and_topics():
    pygame.font.init()
    npc = _npc()
    window = DialogueWindow(pygame.Rect(0, 0, 1000, 500), _ctx(), npc)

    # One greeting line is seeded on open.
    assert window.transcript and window.transcript[0][0] == "npc"
    assert window.name == "Aldric"
    # Roads + news + smalltalk + leave are all offered while rumors exist.
    assert window._topics() == ["roads", "news", "smalltalk", "leave"]


def test_ask_roads_appends_reply_and_logs():
    pygame.font.init()
    logged = []

    def capture(msg, *a, **k):
        logged.append(str(msg))

    esper.set_handler("log_message", capture)  # local name keeps the weak-ref'd handler alive
    window = DialogueWindow(pygame.Rect(0, 0, 1000, 500), _ctx(directions="The road leads to Brackenfen."), _npc())

    window._ask("roads")

    kinds = [k for k, _ in window.transcript]
    assert kinds[-2:] == ["player", "npc"], "roads adds the player's question then the NPC's reply"
    assert window.transcript[-1][1] == "The road leads to Brackenfen."
    assert any("Brackenfen" in m and "[color=yellow]" in m for m in logged), "the reply is mirrored to the log"


def test_ask_roads_with_nothing_new_falls_back():
    pygame.font.init()
    window = DialogueWindow(pygame.Rect(0, 0, 1000, 500), _ctx(directions=None), _npc())
    window._ask("roads")
    assert "road" in window.transcript[-1][1].lower()  # graceful "already told you" line


def test_ask_news_uses_ask_news():
    pygame.font.init()
    window = DialogueWindow(pygame.Rect(0, 0, 1000, 500), _ctx(news="Wolves were spotted near Brackenfen."), _npc())
    window._ask("news")
    assert window.transcript[-1] == ("npc", "Wolves were spotted near Brackenfen.")


def test_farewell_closes():
    pygame.font.init()
    window = DialogueWindow(pygame.Rect(0, 0, 1000, 500), _ctx(), _npc())
    assert not window.wants_to_close
    window._ask("leave")
    assert window.wants_to_close


def test_message_log_persists_across_uisystem_rebuild():
    """UISystem rebuilt on gameplay re-entry must keep the existing history."""
    pygame.font.init()
    from game.systems.ui_system import UISystem

    log = MessageLog(pygame.Rect(0, 0, 100, 100), pygame.font.SysFont(None, 16))
    log.add_message("An earlier event.")
    assert len(log.messages) == 1

    ui = UISystem(MagicMock(), 0, MagicMock(), log)
    assert ui.message_log is log, "the persisted log instance is reused, not replaced"
    assert len(ui.message_log.messages) == 1, "history is preserved across the rebuild"

    # A brand-new session (no persisted log) still gets a fresh one.
    ui2 = UISystem(MagicMock(), 0, MagicMock())
    assert ui2.message_log is not log
    assert ui2.message_log.messages == []
