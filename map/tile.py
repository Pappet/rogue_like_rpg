from enum import Enum, auto
from typing import Optional, Dict

from config import SpriteLayer


class VisibilityState(Enum):
    UNEXPLORED = auto()
    VISIBLE = auto()
    SHROUDED = auto()
    FORGOTTEN = auto()


class Tile:
    """A tile on the map.

    Tiles can be created either from a registry type_id (data-driven) or from
    explicit properties (legacy / fallback). When a type_id is provided, all
    shared properties (walkable, transparent, sprites, color) are initialised
    from the TileRegistry flyweight; instance-specific state (visibility_state,
    rounds_since_seen) is always per-instance.
    """

    def __init__(
        self,
        type_id: Optional[str] = None,
        *,
        transparent: Optional[bool] = None,
        dark: bool = False,
        sprites: Optional[Dict] = None,
    ):
        # Import here to avoid circular imports at module level.
        from map.tile_registry import TileRegistry

        if type_id is not None:
            tile_type = TileRegistry.get(type_id)
            if tile_type is None:
                raise ValueError(
                    f"Tile type '{type_id}' not found in TileRegistry. "
                    "Ensure ResourceLoader.load_tiles() has been called."
                )
            self._type_id: Optional[str] = type_id
            # Copy the sprite dict so mutations are per-instance.
            self.sprites: Dict = dict(tile_type.sprites)
            self.transparent: bool = tile_type.transparent
            self._walkable: Optional[bool] = tile_type.walkable
            self.color = tile_type.color
            self.dark = dark
        else:
            # Legacy construction – explicit properties.
            self._type_id = None
            self.transparent = transparent if transparent is not None else True
            self.dark = dark
            self.sprites = sprites if sprites is not None else {}
            self._walkable = None  # computed from sprites (legacy behaviour)
            self.color = (200, 200, 200)

        # Per-instance mutable state.
        self.visibility_state = VisibilityState.UNEXPLORED
        self.rounds_since_seen = 0

    def set_type(self, type_id: str) -> None:
        """Replace this tile's type, re-initialising shared properties from the registry."""
        from map.tile_registry import TileRegistry

        tile_type = TileRegistry.get(type_id)
        if tile_type is None:
            raise ValueError(
                f"Tile type '{type_id}' not found in TileRegistry."
            )
        self._type_id = type_id
        self.sprites = dict(tile_type.sprites)
        self.transparent = tile_type.transparent
        self._walkable = tile_type.walkable
        self.color = tile_type.color

    @property
    def walkable(self) -> bool:
        """Return the walkable flag.

        For registry-backed tiles this comes directly from the TileType.
        For legacy tiles it is derived from the GROUND sprite value (old behaviour).
        """
        if self._walkable is not None:
            return self._walkable
        # Legacy fallback: derive from sprites.
        if SpriteLayer.GROUND not in self.sprites:
            return False
        return self.sprites[SpriteLayer.GROUND] != "#"
