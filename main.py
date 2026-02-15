import pygame
import sys
from config import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, HEADER_HEIGHT, SIDEBAR_WIDTH, LOG_HEIGHT
from game_states import TitleScreen, Game, WorldMapState
from services.map_service import MapService
from services.render_service import RenderService
from services.resource_loader import ResourceLoader
from components.camera import Camera
from ecs.world import get_world

class GameController:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(SCREEN_TITLE)
        self.clock = pygame.time.Clock()

        self.map_service = MapService()
        self.render_service = RenderService()
        # Viewport is the area not covered by UI Header, Sidebar and Log
        viewport_width = SCREEN_WIDTH - SIDEBAR_WIDTH
        viewport_height = SCREEN_HEIGHT - HEADER_HEIGHT - LOG_HEIGHT
        self.camera = Camera(viewport_width, viewport_height, 0, HEADER_HEIGHT)

        ResourceLoader.load_tiles("assets/data/tile_types.json")
        ResourceLoader.load_entities("assets/data/entities.json")
        ResourceLoader.load_items("assets/data/items.json")
        world = get_world()
        self.map_service.create_village_scenario(world)
        self.map_container = self.map_service.get_active_map()
        
        self.persist = {
            "map_container": self.map_container,
            "render_service": self.render_service,
            "camera": self.camera,
            "map_service": self.map_service
        }
        
        self.states = {
            "TITLE": TitleScreen(),
            "GAME": Game(),
            "WORLD_MAP": WorldMapState(),
        }
        self.state_name = "TITLE"
        self.state = self.states[self.state_name]
        self.state.startup(self.persist)

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.state.get_event(event)

            self.state.update(dt)
            if self.state.done:
                self.flip_state()

            self.state.draw(self.screen)
            pygame.display.flip()

    def flip_state(self):
        next_state = self.state.next_state
        persist = self.state.persist
        self.state.done = False
        self.state_name = next_state
        self.state = self.states[self.state_name]
        self.state.startup(persist)


def main():
    pygame.init()
    game = GameController()
    game.run()

if __name__ == "__main__":
    main()
