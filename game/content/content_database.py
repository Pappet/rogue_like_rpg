"""Bundles all content registries behind a single facade.

The bootstrap loads the default ContentDatabase once; tests can build
isolated instances or simply clear_all() between runs (see conftest).
"""

from dataclasses import dataclass, field

from game.content.dialogue_service import DialogueService, dialogue_service
from game.content.entity_registry import EntityRegistry, entity_registry
from game.content.item_registry import ItemRegistry, item_registry
from game.content.recipe_registry import RecipeRegistry, recipe_registry
from game.content.resource_loader import ResourceLoader
from game.content.schedule_registry import ScheduleRegistry, schedule_registry
from game.map.tile_registry import TileRegistry, tile_registry


@dataclass
class ContentDatabase:
    """All template registries of the game."""

    tiles: TileRegistry = field(default_factory=lambda: tile_registry)
    entities: EntityRegistry = field(default_factory=lambda: entity_registry)
    items: ItemRegistry = field(default_factory=lambda: item_registry)
    recipes: RecipeRegistry = field(default_factory=lambda: recipe_registry)
    schedules: ScheduleRegistry = field(default_factory=lambda: schedule_registry)
    dialogues: DialogueService = field(default_factory=lambda: dialogue_service)

    def load(self, data_dir: str) -> "ContentDatabase":
        """Load all JSON content from data_dir into the registries."""
        ResourceLoader.load_schedules(f"{data_dir}/schedules.json", self.schedules)
        ResourceLoader.load_tiles(f"{data_dir}/tile_types.json", self.tiles)
        ResourceLoader.load_entities(f"{data_dir}/entities.json", self.entities)
        ResourceLoader.load_items(f"{data_dir}/items.json", self.items)
        ResourceLoader.load_recipes(f"{data_dir}/recipes.json", self.recipes)
        self.dialogues.load(f"{data_dir}/dialogues.json")
        return self

    def clear_all(self) -> None:
        """Empty every registry (used by tests)."""
        self.tiles.clear()
        self.entities.clear()
        self.items.clear()
        self.recipes.clear()
        self.schedules.clear()
        self.dialogues.clear()


# Default database wired to the module-level default registries
default_content = ContentDatabase()
