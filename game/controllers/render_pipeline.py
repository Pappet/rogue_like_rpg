"""The draw cycle for the gameplay state.

Order: map -> entities -> debug overlay -> day/night tint -> HUD -> windows.
"""

import esper
import pygame

from game.components import Position


class RenderPipeline:
    def __init__(self, ctx):
        """Args:
            ctx: The shared GameContext.
        """
        self.ctx = ctx

    def _player_layer(self) -> int:
        try:
            return esper.component_for_entity(self.ctx.player_entity, Position).layer
        except KeyError:
            return 0

    def draw(self, surface) -> None:
        ctx = self.ctx
        systems = ctx.systems
        camera = ctx.camera

        surface.fill((0, 0, 0))
        player_layer = self._player_layer()
        viewport_rect = pygame.Rect(camera.offset_x, camera.offset_y, camera.width, camera.height)

        # 1. Render map (clipped to viewport)
        surface.set_clip(viewport_rect)
        if ctx.map_container:
            ctx.render_service.render_map(surface, ctx.map_container, camera, player_layer)

        # 2. Render entities via ECS
        if systems.render_system:
            systems.render_system.process(surface, player_layer)

        # 3. Debug overlay
        if ctx.debug_flags.master and systems.debug_render_system:
            systems.debug_render_system.process(surface, ctx.debug_flags, player_layer)

        # 4. Day/night viewport tint
        tint_color = ctx.world_clock.get_interpolated_tint()
        if tint_color and tint_color[3] > 0:  # Only apply if alpha > 0
            ctx.render_service.apply_viewport_tint(surface, tint_color, viewport_rect)

        # Reset clip for UI
        surface.set_clip(None)

        # 5. HUD and modal windows
        if systems.ui_system:
            systems.ui_system.process(surface)
        ctx.ui_stack.draw(surface)
