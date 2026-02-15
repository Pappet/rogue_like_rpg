import pygame
from config import TILE_SIZE

class DebugRenderSystem:
    def __init__(self, camera, map_container):
        self.camera = camera
        self.map_container = map_container
        pygame.font.init()
        self.font = pygame.font.SysFont("monospace", 12)
        # Create overlay surface with camera dimensions and transparency
        self.overlay = pygame.Surface((camera.width, camera.height), pygame.SRCALPHA)

    def process(self, surface):
        # 1. Clear the overlay
        self.overlay.fill((0, 0, 0, 0))

        # 2. Placeholder: Draw "DEBUG MODE" text
        debug_text = self.font.render("DEBUG MODE", True, (255, 255, 0))
        self.overlay.blit(debug_text, (10, 10))

        # 3. Blit overlay to the main surface at the camera's viewport position
        surface.blit(self.overlay, (self.camera.offset_x, self.camera.offset_y))
