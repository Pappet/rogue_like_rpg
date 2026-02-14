"""Resource loader service.

Responsible for loading game data from disk into in-memory registries.
Call ResourceLoader.load_tiles() during game startup before any map
generation to ensure all tile definitions are available.
"""

import json
import os

from config import SpriteLayer
from map.tile_registry import TileRegistry, TileType


class ResourceLoader:
    """Service that parses JSON resource files and populates registries."""

    @staticmethod
    def load_tiles(filepath: str) -> None:
        """Load tile definitions from a JSON file into TileRegistry.

        Args:
            filepath: Path to the tile_types.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Tile resource file not found: '{filepath}'. "
                f"Expected a JSON file with tile definitions."
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in tile resource file '{filepath}': {exc}"
            ) from exc

        if not isinstance(data, list):
            raise ValueError(
                f"Tile resource file '{filepath}' must contain a JSON array, "
                f"got {type(data).__name__}."
            )

        for item in data:
            # --- validate required fields ---
            for required_field in ("id", "name", "walkable", "transparent"):
                if required_field not in item:
                    raise ValueError(
                        f"Tile entry missing required field '{required_field}': {item}"
                    )

            # --- convert sprite layer string keys to SpriteLayer enum ---
            sprites: dict = {}
            for layer_name, char in item.get("sprites", {}).items():
                try:
                    layer = SpriteLayer[layer_name]
                    sprites[layer] = char
                except KeyError:
                    print(
                        f"Warning: Unknown sprite layer '{layer_name}' in tile "
                        f"'{item['id']}' — skipping that sprite entry."
                    )

            # --- build color tuple ---
            raw_color = item.get("color", [255, 255, 255])
            color = tuple(raw_color)

            tile_type = TileType(
                id=item["id"],
                name=item["name"],
                walkable=bool(item["walkable"]),
                transparent=bool(item["transparent"]),
                sprites=sprites,
                color=color,
                base_description=item.get("base_description", ""),
                occludes_below=bool(item.get("occludes_below", False)),
            )

            TileRegistry.register(tile_type)
