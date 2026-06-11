"""Dialogue Service.

Loads dialogue lines from a JSON file and provides random lines
for NPC interactions based on their entity template ID.

Two JSON formats per template id are supported (ROADMAP Phase D):

  Legacy:      "villager": ["line", ...]
  Conditional: "villager": {
                   "default": ["line", ...],
                   "conditional": [
                       {"when": {"rep": "beloved"}, "lines": [...]},
                       {"when": {"phase": "night"}, "lines": [...]},
                       {"when": {"activity": "WORK"}, "lines": [...]}
                   ]
               }

get_line() picks the FIRST conditional entry whose "when" keys all match
the supplied context dict; otherwise the default pool. The context is
assembled by the caller (rep tier / day phase via the context_provider
wired in bootstrap, activity from the NPC's component).
"""

import json
import logging
import os
import random

logger = logging.getLogger(__name__)


class DialogueService:
    """Read-only service for retrieving NPC dialogue lines."""

    def __init__(self):
        self._dialogues: dict = {}
        # Optional callable returning context keys the game layer knows
        # (rep tier, day phase). Wired once in bootstrap.
        self.context_provider = None
        # Optional callable returning a rumor line (or None). Rumors
        # occasionally replace smalltalk (wired in bootstrap).
        self.rumor_provider = None

    def load(self, filepath: str) -> None:
        """Load dialogue definitions from a JSON file.

        Args:
            filepath: Path to the dialogues.json file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the JSON is malformed.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Dialogue file not found: '{filepath}'")

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in dialogue file '{filepath}': {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"Dialogue file '{filepath}' must contain a JSON object.")

        self._dialogues = data
        logger.info(f"Loaded dialogues for {len(data)} template IDs.")

    def clear(self) -> None:
        """Remove all loaded dialogues (used by tests)."""
        self._dialogues = {}

    def get_line(self, template_id: str, context: dict | None = None) -> str:
        """Return a dialogue line for the given template ID.

        Conditional entries are evaluated against the context dict (first
        match wins); legacy list entries are used as-is. Falls back to
        ``_default`` lines, then to a generic ellipsis.
        """
        entry = self._dialogues.get(template_id)
        if entry is None:
            entry = self._dialogues.get("_default")

        lines = self._select_lines(entry, context or {})
        if not lines:
            return "..."
        return random.choice(lines)

    @staticmethod
    def _select_lines(entry, context: dict) -> list[str] | None:
        """Resolve an entry (legacy list or conditional dict) to a line pool."""
        if entry is None:
            return None
        if isinstance(entry, list):
            return entry
        for conditional in entry.get("conditional", []):
            when = conditional.get("when", {})
            if when and all(context.get(key) == expected for key, expected in when.items()):
                return conditional.get("lines") or None
        return entry.get("default")


# Default instance used by the game
dialogue_service = DialogueService()
