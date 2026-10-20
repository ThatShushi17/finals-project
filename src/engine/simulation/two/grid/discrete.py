import numpy as np
import pandas as pd
import moderngl
from pathlib import Path

from .....settings import Setting, SliderDetails, DropdownDetails
from .....types import SettingsSchema
from ..simulation_2d import Simulation2D
from ....ui.color_scheme import ColorScheme

class DiscreteGridSimulation(Simulation2D):
    GRID_WIDTH = Setting[int](100)
    GRID_HEIGHT = Setting[int](100)
    INITIAL_GRID = Setting[str]("random")

    COMPUTE_SHADER: str | None = None
    PRESET_PATH: Path | None = None
    FRAGMENT_SHADER = (Path(__file__).parent.parent.parent.parent.parent / "shaders/simulation/grid/discrete.frag").read_text(encoding="utf-8")

    @classmethod
    def get_schema(cls) -> SettingsSchema:
        schema = super().get_schema()

        options = ["random"]
        if cls.PRESET_PATH is not None:
            presets = sorted(cls.PRESET_PATH.glob("*.csv"))
            options.extend([*(p.stem for p in presets)])

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
            "initial_grid": DropdownDetails(
                "Initial Grid",
                options=tuple(options),
                setting=cls.INITIAL_GRID,
                placeholder_text="random",
                default_value=cls.INITIAL_GRID.value,
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

        self.camera_x = self.grid_width.value * cell_size / 2  # type: ignore
        self.camera_y = self.grid_height.value * cell_size / 2  # type: ignore

        initial_grid = self._load_initial_grid(
            self.schema["initial_grid"].setting.value  # type: ignore
        )

        self.grid_a = self._create_state_texture(initial_grid)
        self.grid_b = self._create_state_texture(
            np.zeros((self.grid_height.value, self.grid_width.value), dtype=np.uint8)  # type: ignore
        )

        # 0 means A is current; 1 means B is current.
        self._current_grid = 0

        self._render_program = self.ctx.program(
            vertex_shader=self.VERTEX_SHADER,
            fragment_shader=self.FRAGMENT_SHADER,
        )

        self._render_vao = self.ctx.vertex_array(  # type: ignore
            self._render_program,
            [
                (
                    self._quad_buffer,
                    "2f",
                    "in_position"
                )
            ]
        )

    @property
    def current_grid(self) -> moderngl.Texture:
        return self.grid_a if self._current_grid == 0 else self.grid_b

    @property
    def next_grid(self) -> moderngl.Texture:
        return self.grid_b if self._current_grid == 0 else self.grid_a

    def swap_grids(self) -> None:
        self._current_grid = 1 - self._current_grid

    def _load_initial_grid(self, preset_name: str) -> np.ndarray:
        if preset_name == "random" or self.PRESET_PATH is None:
            return np.random.randint(
                0, 2,
                size=(self.grid_height.value, self.grid_width.value),
                dtype=np.uint8,
            )

        path = self.PRESET_PATH / f"{preset_name}.csv"
        grid = pd.read_csv(path, header=None).to_numpy(dtype=np.uint8)

        expected_shape = (self.grid_height.value, self.grid_width.value)
        if grid.shape != expected_shape:
            raise ValueError(
                f"Preset {path.name!r} has shape {grid.shape}; "
                f"expected {expected_shape}."
            )

        return grid

    def _create_state_texture(self, grid: np.ndarray) -> moderngl.Texture:
        texture = self.ctx.texture(
            (self.grid_width.value, self.grid_height.value),
            components=1,
            data=grid.tobytes(order="C"),
            dtype="u1",
            alignment=1,
        )
        texture.filter = (
            moderngl.NEAREST,
            moderngl.NEAREST,
        )
        texture.repeat_x = False
        texture.repeat_y = False
        return texture

    def cleanup(self) -> None:
        self.grid_a.release()
        self.grid_b.release()
        super().cleanup()