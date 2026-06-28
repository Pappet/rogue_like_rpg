"""The draw cycle for the gameplay state.

Order: map -> entities -> debug overlay -> day/night tint -> light glow
-> HUD -> windows.
"""

import esper
import pygame

from config import DN_SETTINGS
from core.ui import theme
from game.components import LightSource, Position

# Tint alpha at which light glow reaches full strength (the night value).
_MAX_TINT_ALPHA = DN_SETTINGS["night"]["tint"][3]


class RenderPipeline:
    def __init__(self, ctx):
        """Args:
        ctx: The shared GameContext.
        """
        self.ctx = ctx

    def _player_pos(self) -> Position | None:
        try:
            return esper.component_for_entity(self.ctx.player_entity, Position)
        except KeyError:
            return None

    def draw(self, surface) -> None:
        ctx = self.ctx
        systems = ctx.systems
        camera = ctx.camera

        surface.fill((0, 0, 0))
        player_pos = self._player_pos()
        player_layer = player_pos.layer if player_pos else 0
        viewport_rect = pygame.Rect(camera.offset_x, camera.offset_y, camera.width, camera.height)

        # Which roof (if any) is peeled away because the player walked under it.
        roof_cutaway = set()
        if ctx.map_container and player_pos:
            roof_cutaway = ctx.map_container.roof_cutaway(player_pos.x, player_pos.y, player_layer)

        # 1. Render map (clipped to viewport)
        surface.set_clip(viewport_rect)
        if ctx.map_container:
            ctx.render_service.render_map(surface, ctx.map_container, camera, player_layer, roof_cutaway)

        # 2. Render entities via ECS
        if systems.render_system:
            systems.render_system.process(surface, player_layer, roof_cutaway)

        # 3. Debug overlay
        if ctx.debug_flags.master and systems.debug_render_system:
            systems.debug_render_system.process(surface, ctx.debug_flags, player_layer)

        # 4. Day/night viewport tint
        tint_color = ctx.world_clock.get_interpolated_tint()
        if tint_color and tint_color[3] > 0:  # Only apply if alpha > 0
            ctx.render_service.apply_viewport_tint(surface, tint_color, viewport_rect)

            # 4.5 Warm glow around light sources — the darker the tint, the
            # stronger the glow, so torches fade in with the dusk.
            strength = tint_color[3] / _MAX_TINT_ALPHA
            lights = [
                (pos.x, pos.y, light.radius)
                for _ent, (pos, light) in esper.get_components(Position, LightSource)
                if pos.layer == player_layer
            ]
            if lights:
                ctx.render_service.render_light_glow(surface, camera, lights, strength)

        # 4.6 Subtle permanent vignette framing the play area for atmosphere.
        theme.draw_vignette(surface, viewport_rect, color=(0, 0, 0), max_alpha=55)

        # Reset clip for UI
        surface.set_clip(None)

        # 5. HUD and modal windows
        if systems.ui_system:
            systems.ui_system.process(surface)
        ctx.ui_stack.draw(surface)
