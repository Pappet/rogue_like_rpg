from typing import List
from map.map_layer import MapLayer
from map.tile import VisibilityState


class MapContainer:
    def __init__(self, layers: List[MapLayer]):
        self.layers = layers

    @property
    def width(self) -> int:
        if not self.layers:
            return 0
        return len(self.layers[0].tiles[0])

    @property
    def height(self) -> int:
        if not self.layers:
            return 0
        return len(self.layers[0].tiles)

    def get_tile(self, x: int, y: int, layer_idx: int = 0):
        """Returns the tile at (x, y) for the specified layer."""
        if layer_idx < 0 or layer_idx >= len(self.layers):
            return None
        layer = self.layers[layer_idx]
        if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[0]):
            return layer.tiles[y][x]
        return None

    def forget_all(self):
        """Transitions all VISIBLE and SHROUDED tiles to FORGOTTEN state."""
        for layer in self.layers:
            for row in layer.tiles:
                for tile in row:
                    if tile.visibility_state in (VisibilityState.VISIBLE, VisibilityState.SHROUDED):
                        tile.visibility_state = VisibilityState.FORGOTTEN
                        tile.rounds_since_seen = 1000 # Ensure it stays forgotten
