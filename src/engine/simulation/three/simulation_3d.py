# pyright: standard

import pygame
import moderngl
import glm
import numpy as np
import struct
from typing import cast

from ....types import SettingsSchema
from ..simulation import Simulation
from ...ui.color_scheme import ColorScheme


def bounding_box_vertices(
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]],
) -> np.ndarray:
    minimum, maximum = bounds
    corners = np.array(
        [
            (minimum[0], minimum[1], minimum[2]),
            (maximum[0], minimum[1], minimum[2]),
            (maximum[0], maximum[1], minimum[2]),
            (minimum[0], maximum[1], minimum[2]),
            (minimum[0], minimum[1], maximum[2]),
            (maximum[0], minimum[1], maximum[2]),
            (maximum[0], maximum[1], maximum[2]),
            (minimum[0], maximum[1], maximum[2]),
        ],
        dtype=np.float32,
    )
    edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7),
    )
    return corners[np.asarray(edges, dtype=np.int32)].reshape((-1, 3))

class Simulation3D(Simulation):
    WORLD_BOUNDS = ((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0))
    BOUNDING_BOX_VERTEX_SHADER = """
    #version 330
    in vec3 in_position;
    uniform mat4 u_view_projection;
    void main() {
        gl_Position = u_view_projection * vec4(in_position, 1.0);
    }
    """
    BOUNDING_BOX_FRAGMENT_SHADER = """
    #version 330
    uniform vec4 u_color;
    out vec4 frag_color;
    void main() {
        frag_color = u_color;
    }
    """

    def __init__(
        self,
        ctx: moderngl.Context,
        schema: SettingsSchema,
        color_scheme: ColorScheme
    ):
        super().__init__(ctx=ctx, schema=schema, color_scheme=color_scheme)

        self.camera_distance = 4.5
        self.camera_pitch = 0.5
        self.camera_yaw = 0.0

        self.color_tex = None
        self.depth_rb = None
        self.fbo = None
        self._bounding_box_program = ctx.program(
            vertex_shader=self.BOUNDING_BOX_VERTEX_SHADER,
            fragment_shader=self.BOUNDING_BOX_FRAGMENT_SHADER,
        )
        self._bounding_box_buffer = ctx.buffer(
            bounding_box_vertices(self.WORLD_BOUNDS).tobytes()
        )
        self._bounding_box_vao = ctx.vertex_array(
            self._bounding_box_program,
            [(self._bounding_box_buffer, "3f", "in_position")],
        )

        width, height = ctx.viewport[2:]
        self.fbo = self._create_fbo(width, height)

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
        self.camera_yaw -= dx * 0.007
        self.camera_pitch += dy * 0.007
        self.camera_pitch = max(-1.4, min(1.4, self.camera_pitch))

        if scroll_dy != 0:
            self.camera_distance = max(
                1.0,
                min(20.0, self.camera_distance - scroll_dy * 0.5),
            )

    def draw_simulation(self, view_projection: glm.mat4) -> None:
        raise NotImplementedError

    def render(self, surf: pygame.Surface, frame_rect: pygame.Rect | None = None) -> None:
        target_rect = surf.get_rect() if frame_rect is None else frame_rect
        width, height = target_rect.size
        if width <= 0 or height <= 0:
            return

        if self.fbo is None:
            return

        if self.fbo.size != (width, height):
            self.fbo = self._create_fbo(width, height)

        old_viewport = self.ctx.viewport
        self.fbo.use()
        self.ctx.viewport = (0, 0, width, height)
        self.ctx.enable(moderngl.DEPTH_TEST)
        try:
            color = self.color_scheme.bg_bold()
            self.fbo.clear(
                color.r / 255.0,
                color.g / 255.0,
                color.b / 255.0,
                color.a / 255.0,
            )

            view_projection = self._get_view_projection(width, height)
            self.draw_simulation(view_projection)
            self._draw_bounding_box(view_projection)

            data = self.fbo.read(components=4, alignment=1)
            img = pygame.image.frombuffer(data, (width, height), "RGBA")
            img = pygame.transform.flip(img, False, True)
            surf.blit(img, target_rect.topleft)
        finally:
            self.ctx.disable(moderngl.DEPTH_TEST)
            screen = getattr(self.ctx, "screen", None)
            if screen is not None:
                screen.use()
            self.ctx.viewport = old_viewport

    def _draw_bounding_box(self, view_projection: glm.mat4) -> None:
        matrix = struct.pack(
            "16f",
            *(
                float(view_projection[column][row])
                for column in range(4)
                for row in range(4)
            ),
        )
        cast(
            moderngl.Uniform,
            self._bounding_box_program["u_view_projection"],
        ).write(matrix)
        color = self.color_scheme.fg_bold()
        cast(moderngl.Uniform, self._bounding_box_program["u_color"]).value = (
            color.r / 255.0,
            color.g / 255.0,
            color.b / 255.0,
            1.0,
        )
        self.ctx.line_width = 1.0
        self._bounding_box_vao.render(
            mode=moderngl.LINES,
            vertices=24,
        )

    def _get_view_projection(self, width: int, height: int) -> glm.mat4:
        cam_x = (
            self.camera_distance
            * glm.cos(self.camera_pitch)
            * glm.sin(self.camera_yaw)
        )
        cam_y = self.camera_distance * glm.sin(self.camera_pitch)
        cam_z = (
            self.camera_distance
            * glm.cos(self.camera_pitch)
            * glm.cos(self.camera_yaw)
        )

        aspect = width / height
        projection = glm.perspective(
            glm.radians(45.0), aspect, 0.1, 100.0
        )
        view = glm.lookAt(
            glm.vec3(cam_x, cam_y, cam_z),
            glm.vec3(0.0, 0.0, 0.0),
            glm.vec3(0.0, 1.0, 0.0),
        )
        return cast(glm.mat4, projection * view)

    def _create_fbo(self, width: int, height: int):
        if self.fbo is not None:
            self.fbo.release()
        if self.color_tex is not None:
            self.color_tex.release()
        if self.depth_rb is not None:
            self.depth_rb.release()

        self.color_tex = self.ctx.texture((width, height), 4)
        self.depth_rb = self.ctx.depth_renderbuffer((width, height))
        return self.ctx.framebuffer(
            self.color_tex,
            self.depth_rb,
        )

    def cleanup(self) -> None:
        self._bounding_box_vao.release()
        self._bounding_box_buffer.release()
        self._bounding_box_program.release()
        if self.fbo is not None:
            self.fbo.release()
            self.fbo = None

        if self.color_tex is not None:
            self.color_tex.release()
            self.color_tex = None

        if self.depth_rb is not None:
            self.depth_rb.release()
            self.depth_rb = None

        super().cleanup()
