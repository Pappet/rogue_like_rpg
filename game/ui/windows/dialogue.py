"""DialogueWindow: a conversation modal for talking with townsfolk.

Pushed onto the UIStack by GameplayState in response to a ``dialogue_requested``
event (bumping a friendly/neutral NPC — see InteractionResolver). Instead of
blurting a single line into the message log, talking now opens a small
conversation where the player picks a topic and reads the reply in place:

    - "Ask about the roads"  -> Wegauskunft (reveals travel routes out of town)
    - "Heard any news?"      -> a rumor / lead about the wider world
    - "Make small talk"      -> the NPC's template smalltalk line
    - "Farewell"             -> close

The roads/news topics are the same world-knowledge channel that used to fire
automatically on a bump; surfacing them as explicit choices is what makes
guidance and rumors feel intentional. Their replies are also mirrored to the
chronicle log so the player keeps a written record of where to go.

Purely presentational: it reads NPC flavour from ``dialogue_service`` and the
world-knowledge replies from ``ctx.rumors`` (RumorService); it never mutates
game state beyond what those services do when asked.
"""

import esper
import pygame

from config import (
    UI_SPACING_X,
    UI_THEME_BORDER,
    UI_THEME_GOLD,
    UI_THEME_INK,
    UI_THEME_INK_DIM,
    UI_THEME_INK_MUTED,
    GameStates,
)
from core.input_manager import InputCommand
from core.ui import theme
from core.ui.window_base import UIWindow
from game.components import Activity, Name, Renderable, TemplateId
from game.content.dialogue_service import dialogue_service

# Topic ids in display order. Availability is decided per-NPC at draw time.
_ROADS = "roads"
_NEWS = "news"
_SMALLTALK = "smalltalk"
_LEAVE = "leave"

_TOPIC_LABELS = {
    _ROADS: "Ask about the roads",
    _NEWS: "Heard any news?",
    _SMALLTALK: "Make small talk",
    _LEAVE: "Farewell",
}


class DialogueWindow(UIWindow):
    """A topic-driven conversation with a single NPC."""

    def __init__(self, rect, ctx, npc_entity):
        super().__init__(rect)
        self.ctx = ctx
        self.npc = npc_entity
        self.input_manager = ctx.input_manager
        self.selected_idx = 0
        self.wants_to_close = False

        self.title_font = theme.get_font(32, display=True)
        self.subtitle_font = theme.get_font(19, italic=True)
        self.glyph_font = theme.get_font(30, bold=True)
        self.body_font = theme.get_font(22)
        self.topic_font = theme.get_font(22)
        self.small_font = theme.get_font(18)

        self.name = self._comp(Name).name if self._comp(Name) else "Stranger"
        rend = self._comp(Renderable)
        self.glyph = rend.sprite if rend else "?"
        self.glyph_color = rend.color if rend else UI_THEME_INK
        tid = self._comp(TemplateId)
        self.role = self._humanize(tid.id) if tid and tid.id else "Townsfolk"

        # Conversation transcript: list of (kind, text). "npc" lines render as
        # speech, "player" lines echo the topic the player chose.
        self.transcript: list[tuple[str, str]] = []
        self._say_npc(self._template_line())

    # --- Entity helpers ------------------------------------------------------

    def _comp(self, comp_type):
        return esper.try_component(self.npc, comp_type)

    @staticmethod
    def _humanize(template_id: str) -> str:
        return template_id.replace("_", " ").title()

    # --- Conversation --------------------------------------------------------

    def _say_npc(self, text: str) -> None:
        self.transcript.append(("npc", text))

    def _say_player(self, text: str) -> None:
        self.transcript.append(("player", text))

    def _dialogue_context(self) -> dict:
        """Build the selection context the same way the bump path does."""
        context = {}
        if dialogue_service.context_provider is not None:
            context.update(dialogue_service.context_provider())
        activity = self._comp(Activity)
        if activity is not None:
            context["activity"] = activity.current_activity
        return context

    def _template_line(self) -> str:
        tid = self._comp(TemplateId)
        return dialogue_service.get_line(tid.id if tid else "", self._dialogue_context())

    def _topics(self) -> list[str]:
        """Topics available right now (roads/news appear only when fruitful)."""
        topics = []
        rumors = self.ctx.rumors
        if rumors is not None:
            topics.append(_ROADS)
            topics.append(_NEWS)
        topics.append(_SMALLTALK)
        topics.append(_LEAVE)
        return topics

    def _ask(self, topic: str) -> None:
        rumors = self.ctx.rumors
        if topic == _ROADS:
            self._say_player("You ask about the roads out of town.")
            line = rumors.directions() if rumors else None
            if line:
                self._say_npc(line)
                esper.dispatch_event("log_message", f"[color=yellow]{self.name}:[/color] {line}")
            else:
                self._say_npc("I've already told you every road I know, friend.")
        elif topic == _NEWS:
            self._say_player("You ask whether they've heard any news.")
            line = rumors.ask_news() if rumors else None
            if line:
                self._say_npc(line)
                esper.dispatch_event("log_message", f"[color=yellow]{self.name}:[/color] {line}")
            else:
                self._say_npc("Nothing new reaches my ears these days.")
        elif topic == _SMALLTALK:
            self._say_player("You make small talk.")
            self._say_npc(self._template_line())
        elif topic == _LEAVE:
            self.wants_to_close = True

    # --- Input ---------------------------------------------------------------

    def handle_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.INVENTORY)
        topics = self._topics()

        if command == InputCommand.CANCEL:
            self.wants_to_close = True
            return True
        if command == InputCommand.MOVE_UP:
            self.selected_idx = (self.selected_idx - 1) % len(topics)
            return True
        if command == InputCommand.MOVE_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(topics)
            return True
        if command == InputCommand.CONFIRM:
            self._ask(topics[min(self.selected_idx, len(topics) - 1)])
            return True

        # Swallow any other key so the gameplay layer behind us stays inert.
        return event.type == pygame.KEYDOWN

    # --- Rendering -----------------------------------------------------------

    @staticmethod
    def _wrap(text: str, font, max_width: int) -> list[str]:
        """Greedy word-wrap ``text`` to ``max_width`` pixels."""
        words = text.split()
        if not words:
            return [""]
        lines, current = [], words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if font.size(trial)[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    def draw(self, surface):
        box_x, box_y, box_w, box_h = self.rect
        pad = UI_SPACING_X

        theme.draw_panel(surface, self.rect)
        self._draw_header(surface, box_x, box_y, pad)
        theme.draw_divider(surface, box_x + pad, box_x + box_w - pad, box_y + 70)

        # Transcript (upper) + topic menu (lower) split.
        topics = self._topics()
        topic_h = len(topics) * 34 + 16
        convo = pygame.Rect(box_x + pad, box_y + 82, box_w - 2 * pad, box_h - 82 - topic_h - 50)
        menu = pygame.Rect(box_x + pad, convo.bottom + 10, box_w - 2 * pad, topic_h)
        self._draw_transcript(surface, convo)
        self._draw_topics(surface, menu, topics)

        theme.draw_text(
            surface,
            "[↑/↓] Choose   [Enter] Ask   [Esc] Leave",
            self.small_font,
            UI_THEME_INK_MUTED,
            (box_x + pad + 4, box_y + box_h - 30),
            shadow=False,
        )

    def _draw_header(self, surface, box_x, box_y, pad):
        # Portrait disc with the NPC's map glyph in its own colour.
        cx, cy, r = box_x + pad + 22, box_y + 34, 24
        pygame.draw.circle(surface, (24, 18, 12), (cx, cy), r)
        pygame.draw.circle(surface, UI_THEME_BORDER, (cx, cy), r, 2)
        theme.draw_text(surface, self.glyph, self.glyph_font, self.glyph_color, (cx, cy), anchor="center", shadow=False)

        theme.draw_text(surface, self.name, self.title_font, UI_THEME_GOLD, (cx + r + 14, box_y + 12))
        theme.draw_text(
            surface, self.role, self.subtitle_font, UI_THEME_INK_MUTED, (cx + r + 16, box_y + 46), shadow=False
        )

    def _draw_transcript(self, surface, body):
        theme.draw_inset(surface, body)
        max_w = body.width - 24
        line_h = self.body_font.get_linesize()

        # Flatten the transcript into wrapped, coloured lines.
        rendered: list[tuple[str, tuple]] = []
        for kind, text in self.transcript:
            if kind == "player":
                for ln in self._wrap(text, self.body_font, max_w):
                    rendered.append((ln, UI_THEME_INK_MUTED))
                continue
            prefix = f"{self.name}: "
            wrapped = self._wrap(prefix + text, self.body_font, max_w)
            for i, ln in enumerate(wrapped):
                rendered.append((ln, UI_THEME_INK if i == 0 else UI_THEME_INK_DIM))
            rendered.append(("", UI_THEME_INK))  # spacer between turns

        # Show the tail that fits, newest pinned to the bottom.
        max_lines = max(1, (body.height - 16) // line_h)
        visible = rendered[-max_lines:]
        y = body.y + 8
        for text, color in visible:
            if text:
                theme.draw_text(surface, text, self.body_font, color, (body.x + 12, y), shadow=False)
            y += line_h

    def _draw_topics(self, surface, menu, topics):
        theme.draw_inset(surface, menu)
        row_h = 34
        for i, topic in enumerate(topics):
            row_y = menu.y + 8 + i * row_h
            highlighted = i == self.selected_idx
            if highlighted:
                theme.draw_selection(surface, (menu.x + 4, row_y - 2, menu.width - 8, row_h - 4))
                theme.draw_text(surface, "❯", self.topic_font, UI_THEME_GOLD, (menu.x + 10, row_y + 2), shadow=False)
            color = UI_THEME_GOLD if highlighted else UI_THEME_INK
            theme.draw_text(
                surface, _TOPIC_LABELS[topic], self.topic_font, color, (menu.x + 34, row_y + 2), shadow=highlighted
            )
