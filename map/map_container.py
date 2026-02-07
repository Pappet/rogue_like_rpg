from typing import List
from map.map_layer import MapLayer


class MapContainer:
    def __init__(self, layers: List[MapLayer]):
        self.layers = layers
