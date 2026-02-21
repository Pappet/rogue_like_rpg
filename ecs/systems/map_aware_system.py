class MapAwareSystem(object):
    def __init__(self):
        self._map_container = None

    def set_map(self, map_container):
        self._map_container = map_container
