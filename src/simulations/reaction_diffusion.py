from pathlib import Path
from typing import cast

import moderngl
import numpy as np
import pandas as pd

from src.engine.simulation import ContinuousGridSimulation
from src.engine.ui.color_scheme import ColorScheme
from src.enums import Accents
from src.settings import DropdownDetails, Setting, SliderDetails
from src.types import SettingsSchema


def _set_uniform(
    program: moderngl.ComputeShader,
    name: str,
    value: object,
) -> None:
    program[name].value = value  # type: ignore


class ReactionDiffusionSimulation(ContinuousGridSimulation):
    METRIC_PLOT_TITLE = "Reaction-diffusion mean concentrations"
    DIFFUSION_A = Setting[float](1.0)
    DIFFUSION_B = Setting[float](0.5)
    FEED_RATE = Setting[float](0.055)
    KILL_RATE = Setting[float](0.062)
    INITIAL_PATTERN = Setting[str]("central_seed")

    COMPUTE_SHADER = (
        Path(__file__).parent.parent
        / "shaders/simulation/compute/reaction_diffusion.comp"
    ).read_text(encoding="utf-8")
    PRESET_PATH = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "presets"
        / "reaction_diffusion"
    )
    RENDER_ACCENT = Accents.ORANGE

    @classmethod
    def get_schema(cls) -> SettingsSchema:
        schema = super().get_schema()
        presets = sorted(ReactionDiffusionSimulation.PRESET_PATH.glob("*.csv"))
        if not presets:
            raise FileNotFoundError(
                "No Reaction-Diffusion CSV presets found in "
                f"{ReactionDiffusionSimulation.PRESET_PATH}."
            )
        default_pattern = (
            "central_seed"
            if any(path.stem == "central_seed" for path in presets)
            else presets[0].stem
        )
        cls.INITIAL_PATTERN.value = default_pattern
        schema.update({
            "initial_pattern": DropdownDetails(
                "Initial Pattern",
                options=tuple(path.stem for path in presets),
                setting=cls.INITIAL_PATTERN,
                placeholder_text=default_pattern,
                default_value=default_pattern,
                initial_only=True,
            ),
            "diffusion_a": SliderDetails(
                "Diffusion A",
                lower_bound=0.0,
                upper_bound=2.0,
                setting=cls.DIFFUSION_A,
            ),
            "diffusion_b": SliderDetails(
                "Diffusion B",
                lower_bound=0.0,
                upper_bound=1.0,
                setting=cls.DIFFUSION_B,
            ),
            "feed_rate": SliderDetails(
                "Feed Rate",
                lower_bound=0.0,
                upper_bound=0.1,
                setting=cls.FEED_RATE,
            ),
            "kill_rate": SliderDetails(
                "Kill Rate",
                lower_bound=0.0,
                upper_bound=0.1,
                setting=cls.KILL_RATE,
            ),
        })
        return schema

    @staticmethod
    def create_initial_grid(
        width: int,
        height: int,
        pattern: str = "central_seed",
    ) -> np.ndarray:
        return ReactionDiffusionSimulation._create_pattern_grid(
            width,
            height,
            pattern,
        )

    @staticmethod
    def _create_pattern_grid(
        width: int,
        height: int,
        pattern: str,
    ) -> np.ndarray:
        preset_path = ReactionDiffusionSimulation.PRESET_PATH / f"{pattern}.csv"
        if not preset_path.is_file():
            raise ValueError(
                f"Unknown reaction-diffusion preset: {pattern!r} "
                f"(expected {preset_path})."
            )

        preset = pd.read_csv(preset_path)
        required_columns = {
            "shape",
            "center_x",
            "center_y",
            "width",
            "height",
            "thickness",
            "concentration_a",
            "concentration_b",
        }
        missing_columns = required_columns.difference(preset.columns)
        if missing_columns:
            raise ValueError(
                f"Preset {preset_path.name!r} is missing columns: "
                + ", ".join(sorted(missing_columns))
            )

        grid = np.zeros((height, width, 2), dtype=np.float32)
        grid[:, :, 0] = 1.0
        x, y = np.meshgrid(
            (np.arange(width, dtype=np.float32) + 0.5) / width,
            (np.arange(height, dtype=np.float32) + 0.5) / height,
        )
        for row in preset.itertuples(index=False):
            shape = str(row.shape)
            center_x = float(str(row.center_x))
            center_y = float(str(row.center_y))
            size_x = float(str(row.width))
            size_y = float(str(row.height))
            delta_x = (x - center_x) / max(size_x * 0.5, 1e-6)
            delta_y = (y - center_y) / max(size_y * 0.5, 1e-6)
            if shape == "ellipse":
                mask = delta_x**2 + delta_y**2 <= 1.0
            elif shape == "rectangle":
                mask = (np.abs(delta_x) <= 1.0) & (np.abs(delta_y) <= 1.0)
            elif shape == "ring":
                radius_squared = delta_x**2 + delta_y**2
                inner_radius = max(
                    0.0,
                    1.0 - 2.0 * float(str(row.thickness)),
                )
                mask = (
                    (radius_squared <= 1.0)
                    & (radius_squared >= inner_radius**2)
                )
            else:
                raise ValueError(
                    f"Preset {preset_path.name!r} uses unknown shape {shape!r}."
                )
            grid[..., 0][mask] = float(str(row.concentration_a))
            grid[..., 1][mask] = float(str(row.concentration_b))

        return grid

    def __init__(
        self,
        ctx: moderngl.Context,
        schema: SettingsSchema,
        color_scheme: ColorScheme,
    ):
        super().__init__(
            ctx=ctx,
            schema=schema,
            color_scheme=color_scheme,
        )
        self._compute_program = self.ctx.compute_shader(self.COMPUTE_SHADER)

    def get_initial_grid(self, width: int, height: int) -> np.ndarray:
        pattern_details = cast(
            DropdownDetails,
            self.schema["initial_pattern"],
        )
        return self._create_pattern_grid(
            width,
            height,
            pattern_details.setting.value,
        )

    def step(self, dt: float) -> None:
        total_time_step = max(dt * 60.0, 0.0)
        if total_time_step == 0.0:
            return

        substep_count = int(np.ceil(total_time_step))
        time_step = total_time_step / substep_count
        program = self._compute_program
        _set_uniform(program, "u_grid_size", (
            self.grid_width.value,
            self.grid_height.value,
        ))
        for setting_name in ("diffusion_a", "diffusion_b", "feed_rate", "kill_rate"):
            details = cast(SliderDetails, self.schema[setting_name])
            _set_uniform(program, f"u_{setting_name}", float(details.setting.value))

        for _ in range(substep_count):
            _set_uniform(program, "u_time_step", time_step)
            self.current_grid.use(location=0)
            self.next_grid.bind_to_image(1, read=False, write=True)

            program.run(
                group_x=(self.grid_width.value + 15) // 16,
                group_y=(self.grid_height.value + 15) // 16,
                group_z=1,
            )
            self.ctx.memory_barrier()
            self.swap_grids()

    def get_metrics(self) -> dict[str, float]:
        grid = np.frombuffer(
            self.current_grid.read(alignment=1),
            dtype=np.float32,
        ).reshape((self.grid_height.value, self.grid_width.value, 2))
        mean_concentrations = grid.mean(axis=(0, 1))
        return {
            "Mean A concentration": float(mean_concentrations[0]),
            "Mean B concentration": float(mean_concentrations[1]),
        }

    def cleanup(self) -> None:
        self._compute_program.release()
        super().cleanup()
