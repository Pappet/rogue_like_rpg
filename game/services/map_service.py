from game.map.map_container import MapContainer


class MapService:
    def __init__(self):
        self.maps: dict[str, MapContainer] = {}
        self.active_map_id: str | None = None

    def register_map(self, map_id: str, container: MapContainer):
        """Registers a map container under a unique ID."""
        self.maps[map_id] = container

    def get_map(self, map_id: str) -> MapContainer | None:
        """Retrieves a map container by its ID."""
        return self.maps.get(map_id)

    def get_active_map(self) -> MapContainer | None:
        """Returns the currently active map container."""
        if self.active_map_id:
            return self.get_map(self.active_map_id)
        return None

    def set_active_map(self, map_id: str):
        """Sets the active map ID."""
        if map_id in self.maps:
            self.active_map_id = map_id
        else:
            raise ValueError(f"Map ID '{map_id}' not found in registry.")
