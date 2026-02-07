from typing import List
from map.tile import Tile


class MapLayer:
    def __init__(self, tiles: List[List[Tile]]):
        self.tiles = tiles
