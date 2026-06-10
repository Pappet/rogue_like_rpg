import esper
import pygame

from config import SCREEN_HEIGHT, SCREEN_WIDTH, GameStates
from core.input_manager import InputCommand
from game.components import Position
from game.map.tile import VisibilityState
from game.states.base import GameState


class WorldMapState(GameState):
    def __init__(self):
        super().__init__()
        self.tile_size = 8
        self.font = pygame.font.Font(None, 36)
        self.title_text = self.font.render("World Map (M/ESC to return)", True, (255, 255, 255))

    def get_event(self, event):
        command = self.input_manager.handle_event(event, GameStates.WORLD_MAP)
        if command == InputCommand.CANCEL:
            self.done = True
            self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.fill((20, 20, 20))
        surface.blit(self.title_text, (20, 20))

        map_container = self.ctx.map_container
        if not map_container or not map_container.layers:
            return

        map_w = map_container.width
        map_h = map_container.height

        # Center the map
        start_x = (SCREEN_WIDTH - map_w * self.tile_size) // 2
        start_y = (SCREEN_HEIGHT - map_h * self.tile_size) // 2

        # Draw ground layer visibility (simplified: top-most visibility wins)
        for y in range(map_h):
            for x in range(map_w):
                tile = map_container.get_tile(x, y, 0)
                if not tile:
                    continue

                rect = pygame.Rect(
                    start_x + x * self.tile_size,
                    start_y + y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )

                color = (0, 0, 0)
                if tile.visibility_state == VisibilityState.VISIBLE:
                    color = (200, 200, 200)  # Light grey
                    if not tile.walkable:
                        color = (100, 100, 100)  # Grey wall
                elif tile.visibility_state == VisibilityState.SHROUDED:
                    color = (60, 60, 60)  # Dark grey
                    if not tile.walkable:
                        color = (40, 40, 40)
                elif tile.visibility_state == VisibilityState.FORGOTTEN:
                    color = (20, 20, 40)  # Very dark blue-grey
                    if not tile.walkable:
                        color = (15, 15, 30)

                if color != (0, 0, 0):
                    pygame.draw.rect(surface, color, rect)

        # Highlight player position
        try:
            player_entity = self.ctx.player_entity
            if player_entity is not None:
                pos = esper.component_for_entity(player_entity, Position)
                p_rect = pygame.Rect(
                    start_x + pos.x * self.tile_size,
                    start_y + pos.y * self.tile_size,
                    self.tile_size,
                    self.tile_size
                )
                pygame.draw.rect(surface, (255, 255, 0), p_rect)  # Yellow player
        except KeyError:
            pass
