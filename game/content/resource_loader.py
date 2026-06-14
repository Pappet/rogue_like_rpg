"""Resource loader service.

Responsible for loading game data from disk into in-memory registries.
Call ResourceLoader.load_tiles() and ResourceLoader.load_entities() during
game startup before any map or entity creation.
"""

import json
import logging
import os

from config import SpriteLayer
from game.components import AIState, Alignment
from game.content.entity_registry import EntityRegistry, EntityTemplate, entity_registry
from game.content.item_registry import ItemRegistry, ItemTemplate, item_registry
from game.content.recipe_registry import Recipe, RecipeRegistry, recipe_registry
from game.content.schedule_registry import ScheduleEntry, ScheduleRegistry, ScheduleTemplate, schedule_registry
from game.map.tile_registry import TileRegistry, TileType, tile_registry

logger = logging.getLogger(__name__)


class ResourceLoader:
    """Service that parses JSON resource files and populates registries."""

    @staticmethod
    def load_schedules(filepath: str, registry: ScheduleRegistry = schedule_registry) -> None:
        """Load schedule definitions from a JSON file into ScheduleRegistry.

        Args:
            filepath: Path to the schedules.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Schedule resource file not found: '{filepath}'.")

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in schedule resource file '{filepath}': {exc}") from exc

        if not isinstance(data, list):
            raise ValueError(f"Schedule resource file '{filepath}' must contain a JSON array.")

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

                target_pool = None
                if entry_data.get("target_pool"):
                    target_pool = [tuple(p) for p in entry_data["target_pool"]]

                route = None
                if entry_data.get("route"):
                    route = [tuple(p) for p in entry_data["route"]]

                entries.append(
                    ScheduleEntry(
                        start=int(entry_data["start"]),
                        end=int(entry_data["end"]),
                        activity=entry_data["activity"],
                        target_pos=target_pos,
                        target_meta=entry_data.get("target_meta"),
                        target_pool=target_pool,
                        route=route,
                    )
                )

            template = ScheduleTemplate(id=item["id"], name=item["name"], entries=entries)
            registry.register(template)

    @staticmethod
    def load_tiles(filepath: str, registry: TileRegistry = tile_registry) -> None:
        """Load tile definitions from a JSON file into TileRegistry.

        Args:
            filepath: Path to the tile_types.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Tile resource file not found: '{filepath}'. Expected a JSON file with tile definitions."
            )

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in tile resource file '{filepath}': {exc}") from exc

        if not isinstance(data, list):
            raise ValueError(f"Tile resource file '{filepath}' must contain a JSON array, got {type(data).__name__}.")

        for item in data:
            # --- validate required fields ---
            for required_field in ("id", "name", "walkable", "transparent"):
                if required_field not in item:
                    raise ValueError(f"Tile entry missing required field '{required_field}': {item}")

            # --- convert sprite layer string keys to SpriteLayer enum ---
            sprites: dict = {}
            for layer_name, char in item.get("sprites", {}).items():
                try:
                    layer = SpriteLayer[layer_name]
                    sprites[layer] = char
                except KeyError:
                    logger.warning(
                        f"Unknown sprite layer '{layer_name}' in tile '{item['id']}' — skipping that sprite entry."
                    )

            # --- per-sprite-layer foreground colors (optional) ---
            sprite_colors: dict = {}
            for layer_name, raw in item.get("sprite_colors", {}).items():
                try:
                    sprite_colors[SpriteLayer[layer_name]] = tuple(raw)
                except KeyError:
                    logger.warning(
                        f"Unknown sprite layer '{layer_name}' in sprite_colors of tile '{item['id']}' — skipping."
                    )

            # --- build color tuples ---
            raw_color = item.get("color", [255, 255, 255])
            color = tuple(raw_color)
            raw_bg = item.get("bg_color")
            bg_color = tuple(raw_bg) if raw_bg is not None else None

            tile_type = TileType(
                id=item["id"],
                name=item["name"],
                walkable=bool(item["walkable"]),
                transparent=bool(item["transparent"]),
                sprites=sprites,
                color=color,
                base_description=item.get("base_description", ""),
                occludes_below=bool(item.get("occludes_below", False)),
                provides_rest=bool(item.get("provides_rest", False)),
                crafting_station=str(item.get("crafting_station", "")),
                bg_color=bg_color,
                sprite_colors=sprite_colors,
            )

            registry.register(tile_type)

    @staticmethod
    def load_entities(filepath: str, registry: EntityRegistry = entity_registry) -> None:
        """Load entity definitions from a JSON file into EntityRegistry.

        Args:
            filepath: Path to the entities.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Entity resource file not found: '{filepath}'. Expected a JSON file with entity definitions."
            )

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in entity resource file '{filepath}': {exc}") from exc

        if not isinstance(data, list):
            raise ValueError(f"Entity resource file '{filepath}' must contain a JSON array, got {type(data).__name__}.")

        required_fields = (
            "id",
            "name",
            "sprite",
            "sprite_layer",
            "hp",
            "max_hp",
            "power",
            "defense",
            "mana",
            "max_mana",
            "perception",
            "intelligence",
        )

        for item in data:
            # --- validate required fields ---
            for required_field in required_fields:
                if required_field not in item:
                    raise ValueError(f"Entity entry missing required field '{required_field}': {item}")

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
                ) from None

            raw_alignment = item.get("alignment", "hostile")
            try:
                Alignment(raw_alignment)
            except ValueError:
                raise ValueError(
                    f"Entity '{item['id']}' has invalid alignment '{raw_alignment}'. "
                    f"Valid values: {[a.value for a in Alignment]}"
                ) from None

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
                merchant=item.get("merchant"),
                needs=item.get("needs"),
                quest_giver=bool(item.get("quest_giver", False)),
                animal=bool(item.get("animal", False)),
                innkeeper=bool(item.get("innkeeper", False)),
            )

            registry.register(template)

    @staticmethod
    def load_items(filepath: str, registry: ItemRegistry = item_registry) -> None:
        """Load item definitions from a JSON file into ItemRegistry.

        Args:
            filepath: Path to the items.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Item resource file not found: '{filepath}'. Expected a JSON file with item definitions."
            )

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in item resource file '{filepath}': {exc}") from exc

        if not isinstance(data, list):
            raise ValueError(f"Item resource file '{filepath}' must contain a JSON array, got {type(data).__name__}.")

        required_fields = ("id", "name", "sprite", "sprite_layer", "weight", "material")

        for item in data:
            # --- validate required fields ---
            for required_field in required_fields:
                if required_field not in item:
                    raise ValueError(f"Item entry missing required field '{required_field}': {item}")

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
                value=int(item.get("value", 0)),
            )

            registry.register(template)

    @staticmethod
    def load_recipes(filepath: str, registry: RecipeRegistry = recipe_registry) -> None:
        """Load crafting recipe definitions from a JSON file (ROADMAP Phase H).

        Args:
            filepath: Path to the recipes.json file.

        Raises:
            FileNotFoundError: If the JSON file does not exist at filepath.
            ValueError: If the JSON is malformed or missing required fields.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"Recipe resource file not found: '{filepath}'. Expected a JSON file with recipe definitions."
            )

        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed JSON in recipe resource file '{filepath}': {exc}") from exc

        if not isinstance(data, list):
            raise ValueError(f"Recipe resource file '{filepath}' must contain a JSON array, got {type(data).__name__}.")

        for item in data:
            for required_field in ("id", "station", "output", "inputs"):
                if required_field not in item:
                    raise ValueError(f"Recipe entry missing required field '{required_field}': {item}")

            registry.register(
                Recipe(
                    id=item["id"],
                    station=item["station"],
                    output=item["output"],
                    inputs={k: int(v) for k, v in item["inputs"].items()},
                    output_qty=int(item.get("output_qty", 1)),
                    ticks=int(item.get("ticks", 30)),
                )
            )
