import moderngl
import numpy as np
import pygame
from pathlib import Path

from src.settings import Setting, SliderDetails
from src.types import SettingsSchema
from src.types import SettingsSchema
from src.enums import Accents
from src.engine.simulation import DiscreteGridSimulation
from src.engine.ui.color_scheme import ColorScheme

class IsingSimulation(DiscreteGridSimulation):
    METRIC_PLOT_TITLE = "Ising magnetization and energy per site"
    TEMPERATURE = Setting[float](2.269)
    COUPLING = Setting[float](1.0)
    EXTERNAL_FIELD = Setting[float](0.0)

    COMPUTE_SHADER = (Path(__file__).parent.parent / "shaders/simulation/compute/ising.comp").read_text(encoding="utf-8")
    PRESET_PATH = Path(__file__).parent.parent.parent / "data/presets/ising"

    @classmethod
    def get_schema(cls) -> SettingsSchema:
        schema = super().get_schema()

        schema.update({
            "temperature": SliderDetails(
                "Temperature",
                lower_bound=0.0,
                upper_bound=5.0,
                setting=cls.TEMPERATURE,
                initial_only=False,
            ),
            "coupling": SliderDetails(
                "Coupling Strength",
                lower_bound=0.0,
                upper_bound=3.0,
                setting=cls.COUPLING,
                initial_only=False,
            ),
            "external_field": SliderDetails(
                "External Field",
                lower_bound=-3.0,
                upper_bound=3.0,
                setting=cls.EXTERNAL_FIELD,
                initial_only=False,
            ),
        })

        return schema

    def __init__(self,
        ctx: moderngl.Context,
        schema: SettingsSchema,
        color_scheme: ColorScheme,
    ):
        super().__init__(
            ctx=ctx,
            schema=schema,
            color_scheme=color_scheme,
        )

        self.state_colors = {
            0: self.color_scheme.accent(Accents.BLUE),  # spin -1
            1: self.color_scheme.accent(Accents.PINK),  # spin +1
        }

        self._ensure_palette()

        self._step_count = 0
        self._sweep_accumulator = 0.0

        if IsingSimulation.COMPUTE_SHADER is None: raise NotImplementedError()
        self._compute_program = self.ctx.compute_shader(IsingSimulation.COMPUTE_SHADER)

    def draw_gpu(self, view_size: tuple[int, int]) -> None:
        self._ensure_palette()

        program = self._render_program

        self.current_grid.use(location=0)
        self._palette_texture.use(location=1)

        program["u_grid"].value = 0  # type: ignore
        program["u_palette"].value = 1  # type: ignore

        program["u_grid_size"].value = (  # type: ignore
            self.grid_width.value,
            self.grid_height.value,
        )
        program["u_view_size"].value = view_size  # type: ignore

        program["u_camera"].value = (  # type: ignore
            self.camera_x,  # type: ignore
            self.camera_y,  # type: ignore
        )
        program["u_zoom"].value = self.zoom  # type: ignore
        program["u_cell_size"].value = float(self.cell_size)  # type: ignore

        program["u_background"].value = self._color_floats(  # type: ignore
            self.color_scheme.bg_bold()
        )
        program["u_grid_line_color"].value = (  # type: ignore
            0.15, 0.15, 0.15, 1.0
        )
        program["u_show_grid"].value = False  # type: ignore

        program["u_outline_color"].value = self._color_floats(
            self.color_scheme.fg_bold()
        )
        self._render_vao.render(
            mode=moderngl.TRIANGLES,
            vertices=3,
        )

    def _ensure_palette(self) -> None:
        palette = bytearray()

        for state in range(256):
            color = pygame.Color(self.state_colors.get(state, self.color_scheme.bg_bold()))
            palette.extend((color.r, color.g, color.b, color.a))

        palette_bytes = bytes(palette)

        if getattr(self, "_palette_texture", None) is None:
            self._palette_texture = self.ctx.texture(
                (256, 1),
                components=4,
                data=palette_bytes,
                dtype="f1",
                alignment=1,
            )
            self._palette_texture.filter = (
                moderngl.NEAREST,
                moderngl.NEAREST,
            )
            self._palette_texture.repeat_x = False
            self._palette_texture.repeat_y = False

        elif getattr(self, "_palette_bytes", None) != palette_bytes:
            self._palette_texture.write(palette_bytes, alignment=1)

        self._palette_bytes = palette_bytes

    def step(self, dt: float) -> None:
        """Run Monte Carlo sweeps at 60 sweeps per simulated second."""
        self._sweep_accumulator += max(dt, 0.0)
        sweep_interval = 1.0 / 60.0
        sweeps = int((self._sweep_accumulator + 1e-12) / sweep_interval)
        if sweeps == 0:
            return

        self._sweep_accumulator -= sweeps * sweep_interval
        for _ in range(sweeps):
            self._sweep()

    def _sweep(self) -> None:
        program = self._compute_program

        program["u_grid_size"].value = (  # type: ignore
            self.grid_width.value,
            self.grid_height.value,
        )
        program["u_temperature"].value = max(  # type: ignore
            0.0, float(self.schema["temperature"].setting.value)  # type: ignore
        )
        program["u_coupling"].value = float(  # type: ignore
            self.schema["coupling"].setting.value  # type: ignore
        )
        program["u_external_field"].value = float(  # type: ignore
            self.schema["external_field"].setting.value  # type: ignore
        )

        local_x, local_y = 16, 16

        groups_x = (self.grid_width.value + local_x - 1) // local_x
        groups_y = (self.grid_height.value + local_y - 1) // local_y

        for parity in (0, 1):
            program["u_parity"].value = parity
            program["u_step"].value = self._step_count

            current = self.current_grid
            next_texture = self.next_grid

            current.use(location=0)
            next_texture.bind_to_image(1, read=False, write=True)

            program.run(
                group_x=groups_x,
                group_y=groups_y,
                group_z=1,
            )

            self.ctx.memory_barrier()
            self.swap_grids()

        self._step_count += 1

    def get_metrics(self) -> dict[str, float]:
        spins = np.frombuffer(
            self.current_grid.read(alignment=1),
            dtype=np.uint8,
        ).reshape((self.grid_height.value, self.grid_width.value))
        spins = spins.astype(np.float32) * 2.0 - 1.0

        horizontal_neighbours = np.roll(spins, 1, axis=1)
        vertical_neighbours = np.roll(spins, 1, axis=0)
        coupling = float(self.schema["coupling"].setting.value)  # type: ignore
        external_field = float(self.schema["external_field"].setting.value)  # type: ignore
        energy_per_site = -coupling * np.mean(
            spins * (horizontal_neighbours + vertical_neighbours)
        ) - external_field * np.mean(spins)

        return {
            "Magnetization": float(np.mean(spins)),
            "Energy / site": float(energy_per_site),
        }