import pygame
import esper
from config import TILE_SIZE, DEBUG_FOV_COLOR, DEBUG_CHASE_COLOR, DEBUG_LABEL_COLOR, DEBUG_FONT_SIZE
from ecs.components import Position, AIBehaviorState, ChaseData, AIState
from map.tile import VisibilityState

class DebugRenderSystem:
    def __init__(self, camera, map_container):
        self.camera = camera
        self.map_container = map_container
        if not pygame.font.get_init():
            pygame.font.init()
        self.font = pygame.font.SysFont("monospace", DEBUG_FONT_SIZE)
        # Create overlay surface with camera dimensions and transparency
        self.overlay = pygame.Surface((camera.width, camera.height), pygame.SRCALPHA)

    def process(self, surface, flags):
        # 1. Clear the overlay
        self.overlay.fill((0, 0, 0, 0))

        # 2. Render Layers
        if flags.get("player_fov", True):
            self._render_fov_overlay()
        if flags.get("npc_fov", False):
            self._render_npc_fov()
        if flags.get("chase", True):
            self._render_chase_targets()
        if flags.get("labels", True):
            self._render_ai_labels()

        # 3. Blit overlay to the main surface at the camera's viewport position
        # The camera offset is applied when blitting the overlay to the screen
        surface.blit(self.overlay, (self.camera.offset_x, self.camera.offset_y))

    def _render_npc_fov(self):
        # Placeholder for future NPC FOV rendering
        pass

    def _render_fov_overlay(self):
        # Calculate visible tile range based on camera position
        # Convert camera pixel coordinates to tile coordinates
        start_col = max(0, self.camera.x // TILE_SIZE)
        start_row = max(0, self.camera.y // TILE_SIZE)
        # Calculate end column and row, ensuring we cover the full viewport
        end_col = min(self.map_container.width, (self.camera.x + self.camera.width) // TILE_SIZE + 1)
        end_row = min(self.map_container.height, (self.camera.y + self.camera.height) // TILE_SIZE + 1)

        # Iterate only visible tiles within the viewport
        for y in range(start_row, end_row):
            for x in range(start_col, end_col):
                # Check visibility on the first layer (ground)
                tile = self.map_container.get_tile(x, y, 0)
                if tile and tile.visibility_state == VisibilityState.VISIBLE:
                    # Calculate position on overlay surface relative to camera viewport
                    screen_x = x * TILE_SIZE - self.camera.x
                    screen_y = y * TILE_SIZE - self.camera.y
                    
                    pygame.draw.rect(
                        self.overlay,
                        DEBUG_FOV_COLOR,
                        (screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                    )

    def _render_ai_labels(self):
        # Iterate over entities with AIBehaviorState and Position
        for ent, (ai_state, pos) in esper.get_components(AIBehaviorState, Position):
            # Calculate screen position relative to camera viewport
            screen_x = pos.x * TILE_SIZE - self.camera.x
            screen_y = pos.y * TILE_SIZE - self.camera.y

            # Check if entity is roughly within viewport (adding margin for labels)
            if -TILE_SIZE < screen_x < self.camera.width and -TILE_SIZE < screen_y < self.camera.height:
                state_code = self._get_state_code(ai_state.state)

                # Fetch ChaseData if it exists to show turns without sight
                if esper.has_component(ent, ChaseData):
                    chase = esper.component_for_entity(ent, ChaseData)
                    state_code += f" T:{chase.turns_without_sight}"

                text_surf = self.font.render(state_code, True, DEBUG_LABEL_COLOR)
                # Draw above the sprite, centered horizontally
                text_rect = text_surf.get_rect(center=(screen_x + TILE_SIZE // 2, screen_y - 10))
                self.overlay.blit(text_surf, text_rect)

    def _get_state_code(self, state_val):
        # state_val is likely an AIState enum member or string
        state_str = str(state_val).lower()
        if "wander" in state_str:
            return "W"
        elif "chase" in state_str:
            return "C"
        elif "idle" in state_str:
            return "I"
        elif "talk" in state_str:
            return "T"
        return "?"

    def _render_chase_targets(self):
        for ent, (chase_data, ai_state, pos) in esper.get_components(ChaseData, AIBehaviorState, Position):
            if ai_state.state == AIState.CHASE:
                # Calculate NPC screen center
                npc_center_x = pos.x * TILE_SIZE - self.camera.x + TILE_SIZE // 2
                npc_center_y = pos.y * TILE_SIZE - self.camera.y + TILE_SIZE // 2

                # Calculate target screen center
                target_x = chase_data.last_known_x
                target_y = chase_data.last_known_y
                target_center_x = target_x * TILE_SIZE - self.camera.x + TILE_SIZE // 2
                target_center_y = target_y * TILE_SIZE - self.camera.y + TILE_SIZE // 2

                # Optimization: Cull if both points are significantly off-screen
                margin = TILE_SIZE * 2
                npc_on_screen = -margin < npc_center_x < self.camera.width + margin and \
                                -margin < npc_center_y < self.camera.height + margin
                target_on_screen = -margin < target_center_x < self.camera.width + margin and \
                                   -margin < target_center_y < self.camera.height + margin

                if npc_on_screen or target_on_screen:
                    # Draw line from NPC to target
                    pygame.draw.line(
                        self.overlay,
                        DEBUG_CHASE_COLOR,
                        (npc_center_x, npc_center_y),
                        (target_center_x, target_center_y),
                        2
                    )

                    # Draw a circle at the target position
                    pygame.draw.circle(
                        self.overlay,
                        DEBUG_CHASE_COLOR,
                        (target_center_x, target_center_y),
                        TILE_SIZE // 4
                    )

                    # Draw outline at target tile
                    pygame.draw.rect(
                        self.overlay,
                        DEBUG_CHASE_COLOR,
                        (target_x * TILE_SIZE - self.camera.x, target_y * TILE_SIZE - self.camera.y, TILE_SIZE, TILE_SIZE),
                        1
                    )