"""Dialogue Service.

Loads dialogue lines from a JSON file and provides random lines
for NPC interactions based on their entity template ID.
"""

import json
import logging
import os
import random

logger = logging.getLogger(__name__)


class DialogueService:
    """Read-only service for retrieving NPC dialogue lines."""

    def __init__(self):
        self._dialogues: dict[str, list[str]] = {}

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

    def get_line(self, template_id: str) -> str:
        """Return a random dialogue line for the given template ID.

        Falls back to ``_default`` lines if the template has no dedicated
        dialogue, and returns a generic fallback if nothing is loaded.
        """
        lines = self._dialogues.get(template_id)
        if not lines:
            lines = self._dialogues.get("_default")
        if not lines:
            return "..."
        return random.choice(lines)


# Default instance used by the game
dialogue_service = DialogueService()
