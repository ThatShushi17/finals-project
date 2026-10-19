import moderngl
import numpy as np
from pathlib import Path

from .....settings import Setting, SliderDetails
from .....types import SettingsSchema
from .....enums import Accents
from ..simulation_2d import Simulation2D
from ....ui.color_scheme import ColorScheme


class ContinuousGridSimulation(Simulation2D):
    GRID_WIDTH = Setting[int](256)
    GRID_HEIGHT = Setting[int](256)
    RENDER_ACCENT = Accents.BLUE

    FRAGMENT_SHADER = (
        Path(__file__).parent.parent.parent.parent.parent
        / "shaders/simulation/grid/continuous.frag"
    ).read_text(encoding="utf-8")

    @classmethod
    def get_schema(cls) -> SettingsSchema:
        schema = super().get_schema()
        schema.update({
            "grid_width": SliderDetails(
                "Grid Width",
                lower_bound=16,
                upper_bound=1024,
                setting=cls.GRID_WIDTH,
                initial_only=True,
            ),
            "grid_height": SliderDetails(
                "Grid Height",
                lower_bound=16,
                upper_bound=1024,
                setting=cls.GRID_HEIGHT,
                initial_only=True,
            ),
        })
        return schema

    def __init__(
        self,
        ctx: moderngl.Context,
        schema: SettingsSchema,
        color_scheme: ColorScheme,
        cell_size: int = 4,
    ):
        super().__init__(
            ctx=ctx,
            schema=schema,
            color_scheme=color_scheme,
        )

        self.grid_width: Setting[int] = schema["grid_width"].setting  # type: ignore
        self.grid_height: Setting[int] = schema["grid_height"].setting  # type: ignore
        self.cell_size = cell_size
        self.camera_x = self.grid_width.value * cell_size / 2
        self.camera_y = self.grid_height.value * cell_size / 2

        initial_grid = self.get_initial_grid(
            self.grid_width.value,
            self.grid_height.value,
        )
        expected_shape = (self.grid_height.value, self.grid_width.value, 2)
        if initial_grid.shape != expected_shape:
            raise ValueError(
                f"Initial continuous grid has shape {initial_grid.shape}; "
                f"expected {expected_shape}."
            )
        if not np.isfinite(initial_grid).all():
            raise ValueError("Initial continuous grid values must be finite.")

        self.grid_a = self._create_state_texture(initial_grid)
        self.grid_b = self._create_state_texture(np.zeros_like(initial_grid))
        self._current_grid = 0

        self._render_program = self.ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER,
        )
        self._render_vao = self.ctx.vertex_array(
            self._render_program,
            [(self._quad_buffer, "2f", "in_position")],
        )

    @staticmethod
    def create_initial_grid(width: int, height: int) -> np.ndarray:
        raise NotImplementedError

    def get_initial_grid(self, width: int, height: int) -> np.ndarray:
        return self.create_initial_grid(width, height)

    @property
    def current_grid(self) -> moderngl.Texture:
        return self.grid_a if self._current_grid == 0 else self.grid_b

    @property
    def next_grid(self) -> moderngl.Texture:
        return self.grid_b if self._current_grid == 0 else self.grid_a

    def swap_grids(self) -> None:
        self._current_grid = 1 - self._current_grid

    def _create_state_texture(self, grid: np.ndarray) -> moderngl.Texture:
        texture = self.ctx.texture(
            (self.grid_width.value, self.grid_height.value),
            components=2,
            data=np.asarray(grid, dtype=np.float32).tobytes(order="C"),
            dtype="f4",
            alignment=1,
        )
        texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
        texture.repeat_x = False
        texture.repeat_y = False
        return texture

    def draw_gpu(self, view_size: tuple[int, int]) -> None:
        program = self._render_program
        self.current_grid.use(location=0)

        program["u_grid"].value = 0
        program["u_grid_size"].value = (
            self.grid_width.value,
            self.grid_height.value,
        )
        program["u_view_size"].value = view_size
        program["u_camera"].value = (self.camera_x, self.camera_y)
        program["u_zoom"].value = self.zoom
        program["u_cell_size"].value = float(self.cell_size)
        program["u_background"].value = self._color_floats(
            self.color_scheme.bg_bold()
        )
        program["u_active_color"].value = self._color_floats(
            self.color_scheme.accent(self.RENDER_ACCENT)
        )
        program["u_grid_line_color"].value = (0.15, 0.15, 0.15, 1.0)
        program["u_show_grid"].value = False

        program["u_outline_color"].value = self._color_floats(
            self.color_scheme.fg_bold()
        )
        self._render_vao.render(
            mode=moderngl.TRIANGLES,
            vertices=3,
        )

    def cleanup(self) -> None:
        self.grid_a.release()
        self.grid_b.release()
        self._render_vao.release()
        self._render_program.release()
        super().cleanup()
