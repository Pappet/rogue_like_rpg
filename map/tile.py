from typing import Optional

from config import SpriteLayer


class Tile:
    """A tile on the map."""
    def __init__(self, transparent: bool, dark: bool, sprites: Optional[dict] = None):
        self.transparent = transparent
        self.dark = dark
        self.sprites = sprites if sprites is not None else {}

    @property
    def walkable(self) -> bool:
        """A tile is walkable if it has a ground sprite."""
        return SpriteLayer.GROUND in self.sprites
