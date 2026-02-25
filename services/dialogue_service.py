"""Dialogue Service.

Loads dialogue lines from a JSON file and provides random lines
for NPC interactions based on their entity template ID.
"""

import json
import os
import random
import logging

logger = logging.getLogger(__name__)


class DialogueService:
    """Read-only service for retrieving NPC dialogue lines."""

    _dialogues: dict[str, list[str]] = {}

    @classmethod
    def load(cls, filepath: str) -> None:
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
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in dialogue file '{filepath}': {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"Dialogue file '{filepath}' must contain a JSON object."
            )

        cls._dialogues = data
        logger.info(f"Loaded dialogues for {len(data)} template IDs.")

    @classmethod
    def get_line(cls, template_id: str) -> str:
        """Return a random dialogue line for the given template ID.

        Falls back to ``_default`` lines if the template has no dedicated
        dialogue, and returns a generic fallback if nothing is loaded.
        """
        lines = cls._dialogues.get(template_id)
        if not lines:
            lines = cls._dialogues.get("_default")
        if not lines:
            return "..."
        return random.choice(lines)
