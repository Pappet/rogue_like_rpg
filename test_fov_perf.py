import time

from core.visibility_service import VisibilityService


class DummyTile:
    def __init__(self, t):
        self.is_transparent = t


class DummyLayer:
    def __init__(self, w, h):
        self.tiles = [[DummyTile(True) for _ in range(w)] for _ in range(h)]


class DummyMapContainer:
    def __init__(self):
        self.layers = [DummyLayer(100, 100)]


map_container = DummyMapContainer()


def get_is_transparent_old(layer_index):
    def is_transparent(x, y):
        if 0 <= layer_index < len(map_container.layers):
            layer = map_container.layers[layer_index]
            if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[y]):
                tile = layer.tiles[y][x]
                return tile.is_transparent
        return False

    return is_transparent


def get_is_transparent_new(layer_index):
    if not (0 <= layer_index < len(map_container.layers)):
        return lambda x, y: False

    layer = map_container.layers[layer_index]
    tiles = layer.tiles
    height = len(tiles)
    width = len(tiles[0]) if height > 0 else 0

    def is_transparent(x, y):
        if 0 <= y < height and 0 <= x < width:
            return tiles[y][x].is_transparent
        return False

    return is_transparent


def test():
    f_old = get_is_transparent_old(0)
    f_new = get_is_transparent_new(0)

    start = time.perf_counter()
    for _ in range(1000):
        VisibilityService.compute_visibility((50, 50), 20, f_old)
    t_old = time.perf_counter() - start

    start = time.perf_counter()
    for _ in range(1000):
        VisibilityService.compute_visibility((50, 50), 20, f_new)
    t_new = time.perf_counter() - start

    print(f"Old: {t_old:.4f}s")
    print(f"New: {t_new:.4f}s")
    print(f"Improvement: {(t_old - t_new) / t_old * 100:.1f}%")


if __name__ == "__main__":
    test()
