"""Resource loader service.

Responsible for loading game data from disk into in-memory registries.
Call ResourceLoader.load_tiles() and ResourceLoader.load_entities() during
game startup before any map or entity creation.
"""

import json
import os
import logging

from config import SpriteLayer

logger = logging.getLogger(__name__)
from ecs.components import AIState, Alignment
from map.tile_registry import TileRegistry, TileType
from entities.entity_registry import EntityRegistry, EntityTemplate
from entities.item_registry import ItemRegistry, ItemTemplate
from entities.schedule_registry import schedule_registry, ScheduleTemplate, ScheduleEntry


class ResourceLoader:
    """Service that parses JSON resource files and populates registries."""

    @staticmethod
    def load_schedules(filepath: str) -> None:
        """Load schedule definitions from a JSON file into ScheduleRegistry.

        Args:
            filepath: Path to the schedules.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Schedule resource file not found: '{filepath}'."
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in schedule resource file '{filepath}': {exc}"
            ) from exc

        if not isinstance(data, list):
            raise ValueError(
                f"Schedule resource file '{filepath}' must contain a JSON array."
            )

        for item in data:
            # Validate required fields
            for field in ("id", "name", "entries"):
                if field not in item:
                    raise ValueError(f"Schedule entry missing required field '{field}': {item}")

            entries = []
            for entry_data in item["entries"]:
                # Validate entry required fields
                for field in ("start", "end", "activity"):
                    if field not in entry_data:
                        raise ValueError(f"Schedule entry data missing '{field}': {entry_data}")

                target_pos = None
                if "target_pos" in entry_data and entry_data["target_pos"] is not None:
                    target_pos = tuple(entry_data["target_pos"])

                entries.append(ScheduleEntry(
                    start=int(entry_data["start"]),
                    end=int(entry_data["end"]),
                    activity=entry_data["activity"],
                    target_pos=target_pos,
                    target_meta=entry_data.get("target_meta")
                ))

            template = ScheduleTemplate(
                id=item["id"],
                name=item["name"],
                entries=entries
            )
            schedule_registry.register(template)

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
                    logger.warning(
                        f"Unknown sprite layer '{layer_name}' in tile "
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

    @staticmethod
    def load_entities(filepath: str) -> None:
        """Load entity definitions from a JSON file into EntityRegistry.

        Args:
            filepath: Path to the entities.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Entity resource file not found: '{filepath}'. "
                f"Expected a JSON file with entity definitions."
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in entity resource file '{filepath}': {exc}"
            ) from exc

        if not isinstance(data, list):
            raise ValueError(
                f"Entity resource file '{filepath}' must contain a JSON array, "
                f"got {type(data).__name__}."
            )

        required_fields = (
            "id", "name", "sprite", "sprite_layer",
            "hp", "max_hp", "power", "defense",
            "mana", "max_mana", "perception", "intelligence",
        )

        for item in data:
            # --- validate required fields ---
            for required_field in required_fields:
                if required_field not in item:
                    raise ValueError(
                        f"Entity entry missing required field '{required_field}': {item}"
                    )

            # --- build color tuple (default white if missing) ---
            raw_color = item.get("color", [255, 255, 255])
            color = tuple(raw_color)

            # --- parse optional bool fields with defaults ---
            ai = bool(item.get("ai", True))
            blocker = bool(item.get("blocker", True))

            # --- parse and validate AI state fields ---
            raw_state = item.get("default_state", "wander")
            try:
                AIState(raw_state)
            except ValueError:
                raise ValueError(
                    f"Entity '{item['id']}' has invalid default_state '{raw_state}'. "
                    f"Valid values: {[s.value for s in AIState]}"
                )

            raw_alignment = item.get("alignment", "hostile")
            try:
                Alignment(raw_alignment)
            except ValueError:
                raise ValueError(
                    f"Entity '{item['id']}' has invalid alignment '{raw_alignment}'. "
                    f"Valid values: {[a.value for a in Alignment]}"
                )

            # --- parse optional description fields ---
            description = item.get("description", "")
            wounded_text = item.get("wounded_text", "")
            wounded_threshold = float(item.get("wounded_threshold", 0.5))
            loot_table = item.get("loot_table", [])
            schedule_id = item.get("schedule_id")
            home_pos = None
            if "home_pos" in item and item["home_pos"] is not None:
                home_pos = tuple(item["home_pos"])

            template = EntityTemplate(
                id=item["id"],
                name=item["name"],
                sprite=item["sprite"],
                color=color,
                sprite_layer=item["sprite_layer"],  # Raw string, NOT converted to enum here
                hp=int(item["hp"]),
                max_hp=int(item["max_hp"]),
                power=int(item["power"]),
                defense=int(item["defense"]),
                mana=int(item["mana"]),
                max_mana=int(item["max_mana"]),
                perception=int(item["perception"]),
                intelligence=int(item["intelligence"]),
                ai=ai,
                blocker=blocker,
                default_state=raw_state,
                alignment=raw_alignment,
                description=description,
                wounded_text=wounded_text,
                wounded_threshold=wounded_threshold,
                loot_table=loot_table,
                schedule_id=schedule_id,
                home_pos=home_pos,
            )

            EntityRegistry.register(template)

    @staticmethod
    def load_items(filepath: str) -> None:
        """Load item definitions from a JSON file into ItemRegistry.

        Args:
            filepath: Path to the items.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Item resource file not found: '{filepath}'. "
                f"Expected a JSON file with item definitions."
            )

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Malformed JSON in item resource file '{filepath}': {exc}"
            ) from exc

        if not isinstance(data, list):
            raise ValueError(
                f"Item resource file '{filepath}' must contain a JSON array, "
                f"got {type(data).__name__}."
            )

        required_fields = ("id", "name", "sprite", "sprite_layer", "weight", "material")

        for item in data:
            # --- validate required fields ---
            for required_field in required_fields:
                if required_field not in item:
                    raise ValueError(
                        f"Item entry missing required field '{required_field}': {item}"
                    )

            # --- build color tuple ---
            raw_color = item.get("color", [255, 255, 255])
            color = tuple(raw_color)

            template = ItemTemplate(
                id=item["id"],
                name=item["name"],
                sprite=item["sprite"],
                color=color,
                sprite_layer=item["sprite_layer"],
                weight=float(item["weight"]),
                material=item["material"],
                description=item.get("description", ""),
                slot=item.get("slot"),
                stats=item.get("stats", {}),
                consumable=item.get("consumable"),
            )

            ItemRegistry.register(template)
