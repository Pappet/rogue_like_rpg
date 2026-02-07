from config import TILE_SIZE

class Camera:
    def __init__(self, width, height):
        self.x = 0
        self.y = 0
        self.width = width
        self.height = height

    def apply(self, entity):
        """Adjusts an entity's position based on the camera's position."""
        return entity.x - self.x, entity.y - self.y

    def apply_to_pos(self, x, y):
        """Adjusts a world position (x, y) based on the camera's position."""
        return x - self.x, y - self.y

    def screen_to_tile(self, screen_x, screen_y):
        """Converts screen coordinates to tile coordinates."""
        world_x = screen_x + self.x
        world_y = screen_y + self.y
        return world_x // TILE_SIZE, world_y // TILE_SIZE

    def tile_to_screen(self, tile_x, tile_y):
        """Converts tile coordinates to screen coordinates."""
        pixel_x = tile_x * TILE_SIZE
        pixel_y = tile_y * TILE_SIZE
        return self.apply(pixel_x, pixel_y)
