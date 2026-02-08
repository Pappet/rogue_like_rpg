from typing import List
from map.map_layer import MapLayer
from map.tile import VisibilityState


class MapContainer:
    def __init__(self, layers: List[MapLayer]):
        self.layers = layers

    def forget_all(self):
        """Transitions all VISIBLE and SHROUDED tiles to FORGOTTEN state."""
        for layer in self.layers:
            for row in layer.tiles:
                for tile in row:
                    if tile.visibility_state in (VisibilityState.VISIBLE, VisibilityState.SHROUDED):
                        tile.visibility_state = VisibilityState.FORGOTTEN
                        tile.rounds_since_seen = 1000 # Ensure it stays forgotten
