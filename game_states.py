import pygame
from enum import Enum, auto
from config import SpriteLayer
from services.party_service import PartyService

class GameStates(Enum):
    PLAYER_TURN = auto()
    ENEMY_TURN = auto()

class GameState:
    def __init__(self):
        self.done = False
        self.next_state = None

    def startup(self, persistent):
        self.persist = persistent

    def get_event(self, event):
        raise NotImplementedError

    def update(self, dt):
        raise NotImplementedError

    def draw(self, surface):
        raise NotImplementedError


class TitleScreen(GameState):
    def __init__(self):
        super().__init__()
        self.font = pygame.font.Font(None, 74)
        self.title_text = self.font.render("Rogue Like RPG", True, (255, 255, 255))
        self.title_rect = self.title_text.get_rect(center=(400, 200))

        self.button_font = pygame.font.Font(None, 50)
        self.button_text = self.button_font.render("New Game", True, (255, 255, 255))
        self.button_rect = pygame.Rect(300, 300, 200, 50)

    def get_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.button_rect.collidepoint(event.pos):
                self.done = True
                self.next_state = "GAME"

    def update(self, dt):
        pass

    def draw(self, surface):
        surface.blit(self.title_text, self.title_rect)
        pygame.draw.rect(surface, (100, 100, 100), self.button_rect)
        surface.blit(self.button_text, (self.button_rect.x + 20, self.button_rect.y + 10))


class Game(GameState):
    def __init__(self):
        super().__init__()
        self.map_container = None
        self.render_service = None
        self.turn_service = None
        self.camera = None
        self.player = None

    def startup(self, persistent):
        self.persist = persistent
        self.map_container = self.persist.get("map_container")
        self.render_service = self.persist.get("render_service")
        self.turn_service = self.persist.get("turn_service")
        self.camera = self.persist.get("camera")
        
        if not self.persist.get("player"):
            party_service = PartyService()
            # Start at 1,1 to avoid the wall at 0,0
            self.player = party_service.create_initial_party(1, 1)
            self.persist["player"] = self.player
            
            # Place player on map
            self._update_player_tile(None, (self.player.x, self.player.y))
        else:
            self.player = self.persist.get("player")

    def _get_tile(self, x, y):
        if self.map_container and self.map_container.layers:
            layer = self.map_container.layers[0] # Assume first layer for now
            if 0 <= y < len(layer.tiles) and 0 <= x < len(layer.tiles[0]):
                return layer.tiles[y][x]
        return None

    def _update_player_tile(self, old_pos, new_pos):
        if old_pos:
            old_tile = self._get_tile(*old_pos)
            if old_tile and SpriteLayer.ENTITIES in old_tile.sprites:
                del old_tile.sprites[SpriteLayer.ENTITIES]
        
        new_tile = self._get_tile(*new_pos)
        if new_tile:
            new_tile.sprites[SpriteLayer.ENTITIES] = self.player.sprite

    def get_event(self, event):
        if self.turn_service and not self.turn_service.is_player_turn():
            return

        if event.type == pygame.KEYDOWN:
            dx, dy = 0, 0
            if event.key == pygame.K_UP:
                dy = -1
            elif event.key == pygame.K_DOWN:
                dy = 1
            elif event.key == pygame.K_LEFT:
                dx = -1
            elif event.key == pygame.K_RIGHT:
                dx = 1
            
            if dx != 0 or dy != 0:
                self.move_player(dx, dy)

    def move_player(self, dx, dy):
        new_x = self.player.x + dx
        new_y = self.player.y + dy
        
        target_tile = self._get_tile(new_x, new_y)
        if target_tile and target_tile.walkable:
            old_pos = (self.player.x, self.player.y)
            self.player.x = new_x
            self.player.y = new_y
            self._update_player_tile(old_pos, (new_x, new_y))
            
            if self.turn_service:
                self.turn_service.end_player_turn()

    def update(self, dt):
        if self.camera and self.player:
            self.camera.update(self.player.x, self.player.y)

    def draw(self, surface):
        surface.fill((0, 0, 0))
        if self.render_service and self.map_container and self.camera:
            self.render_service.render_map(surface, self.map_container, self.camera)
