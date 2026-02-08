from enum import Enum, auto
from typing import Optional

from config import SpriteLayer


class VisibilityState(Enum):
    UNEXPLORED = auto()
    VISIBLE = auto()
    SHROUDED = auto()
    FORGOTTEN = auto()


class Tile:
    """A tile on the map."""
    def __init__(self, transparent: bool, dark: bool, sprites: Optional[dict] = None):
        self.transparent = transparent
        self.dark = dark
        self.sprites = sprites if sprites is not None else {}
        self.visibility_state = VisibilityState.UNEXPLORED
        self.rounds_since_seen = 0

    @property
    def walkable(self) -> bool:
        """A tile is walkable if it has a ground sprite and it's not a wall."""
        if SpriteLayer.GROUND not in self.sprites:
            return False
        return self.sprites[SpriteLayer.GROUND] != "#"
