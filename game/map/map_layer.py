from game.map.tile import Tile


class MapLayer:
    def __init__(self, tiles: list[list[Tile]]):
        self.tiles = tiles

    @property
    def width(self) -> int:
        if not self.tiles:
            return 0
        return len(self.tiles[0])

    @property
    def height(self) -> int:
        return len(self.tiles)
