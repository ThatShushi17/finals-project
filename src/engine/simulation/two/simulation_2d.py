import struct
import pygame
import moderngl

from ....types import SettingsSchema
from ..simulation import Simulation
from ...ui.color_scheme import ColorScheme


class Simulation2D(Simulation):
    MIN_ZOOM = 0.1
    MAX_ZOOM = 20.0
    ZOOM_FACTOR = 1.12
    VERTEX_SHADER = """
    #version 330

    in vec2 in_position;

    void main() {
        gl_Position = vec4(in_position, 0.0, 1.0);
    }
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        schema: SettingsSchema,
        color_scheme: ColorScheme
    ):
        super().__init__(ctx=ctx, schema=schema, color_scheme=color_scheme)

        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0

        # Shared full-screen triangle. Subclasses create their own VAOs
        # using this buffer and their own shader programs.
        self._quad_buffer = ctx.buffer(
            struct.pack(
                "6f",
                -1.0, -1.0,
                 3.0, -1.0,
                -1.0,  3.0,
            )
        )

        # Reusable GPU render target; resized only when necessary.
        self._render_texture: moderngl.Texture | None = None
        self._render_fbo: moderngl.Framebuffer | None = None
        self._render_size: tuple[int, int] | None = None
        self._render_image_data: bytes | None = None

    @staticmethod
    def _color_floats(color: pygame.Color) -> tuple[float, float, float, float]:
        return (
            color.r / 255.0,
            color.g / 255.0,
            color.b / 255.0,
            color.a / 255.0,
        )

    def _ensure_render_target(self, width: int, height: int) -> None:
        size = (width, height)

        if self._render_size == size:
            return

        if self._render_fbo is not None:
            self._render_fbo.release()
            self._render_fbo = None

        if self._render_texture is not None:
            self._render_texture.release()
            self._render_texture = None

        self._render_texture = self.ctx.texture(
            size,
            components=4,
            dtype="f1",
        )
        self._render_texture.filter = (
            moderngl.NEAREST,
            moderngl.NEAREST,
        )

        self._render_fbo = self.ctx.framebuffer(
            color_attachments=[self._render_texture]
        )
        self._render_size = size

    def process_mouse(
        self,
        dx: int,
        dy: int,
        scroll_dy: int,
        *,
        panning: bool = False,
        mouse_pos: tuple[int, int] | None = None,
        frame_rect: pygame.Rect | None = None,
    ) -> None:
        if panning:
            self.camera_x -= dx / self.zoom
            self.camera_y -= dy / self.zoom

        if scroll_dy == 0:
            return

        old_zoom = self.zoom
        self.zoom = max(
            self.MIN_ZOOM,
            min(
                self.MAX_ZOOM,
                self.zoom * self.ZOOM_FACTOR ** scroll_dy,
            ),
        )

        if mouse_pos is None or frame_rect is None:
            return

        mouse_x, mouse_y = mouse_pos
        centre_x, centre_y = frame_rect.center

        world_x = self.camera_x + (mouse_x - centre_x) / old_zoom
        world_y = self.camera_y + (mouse_y - centre_y) / old_zoom

        self.camera_x = world_x - (mouse_x - centre_x) / self.zoom
        self.camera_y = world_y - (mouse_y - centre_y) / self.zoom

    def world_to_screen(self, x: float, y: float, frame_rect: pygame.Rect) -> tuple[int, int]:
        return (
            round(frame_rect.centerx + (x - self.camera_x) * self.zoom),
            round(frame_rect.centery + (y - self.camera_y) * self.zoom),
        )

    def screen_to_world(self, x: float, y: float, frame_rect: pygame.Rect) -> tuple[float, float]:
        return (
            self.camera_x + (x - frame_rect.centerx) / self.zoom,
            self.camera_y + (y - frame_rect.centery) / self.zoom,
        )

    def draw_gpu(self, view_size: tuple[int, int]) -> None:
        raise NotImplementedError

    def render(self, surf: pygame.Surface, frame_rect: pygame.Rect | None = None) -> None:
        if frame_rect is None:
            frame_rect = surf.get_rect()

        width, height = frame_rect.size

        if width <= 0 or height <= 0:
            return

        self._ensure_render_target(width, height)
        assert self._render_fbo is not None

        old_viewport = self.ctx.viewport
        old_clip = surf.get_clip()

        try:
            self._render_fbo.use()
            self.ctx.viewport = (0, 0, width, height)

            self.ctx.disable(moderngl.DEPTH_TEST)
            self.ctx.disable(moderngl.BLEND)

            color = self.color_scheme.bg_bold()
            self._render_fbo.clear(
                *self._color_floats(color)
            )

            self.draw_gpu((width, height))

            data = self._render_fbo.read(
                components=4,
                alignment=1,
            )
            self._render_image_data = data
            image = pygame.image.frombuffer(data, (width, height), "RGBA")

            surf.set_clip(old_clip.clip(frame_rect))
            surf.blit(image, frame_rect.topleft)

        finally:
            surf.set_clip(old_clip)

            screen = getattr(self.ctx, "screen", None)
            if screen is not None:
                screen.use()

            self.ctx.viewport = old_viewport

    def cleanup(self) -> None:
        if self._render_fbo is not None:
            self._render_fbo.release()
            self._render_fbo = None

        if self._render_texture is not None:
            self._render_texture.release()
            self._render_texture = None

        self._render_image_data = None
        self._quad_buffer.release()
        super().cleanup()