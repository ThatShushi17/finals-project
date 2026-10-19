import pygame
import moderngl
import pandas as pd
from collections import deque
from pathlib import Path
from typing import Any, cast

from ...types import SettingsSchema
from ...settings import (
    CheckboxDetails,
    CompoundDetails,
    DropdownDetails,
    InputDetails,
    ListDetails,
    Setting,
    SliderDetails,
)
from ..ui.color_scheme import ColorScheme

class Simulation:
    HISTORY_LIMIT = 2000
    DEFAULT_DATA_COLLECTION_INTERVAL = 0.1
    READINGS_ROOT = Path(__file__).resolve().parents[3] / "data" / "readings"
    SIMULATION_SPEED = Setting[float](1.0)
    RECORD_CSV = Setting[bool](False)
    CSV_FILENAME = Setting[str]("simulation_data")

    def __init__(
        self,
        ctx: moderngl.Context,
        schema: SettingsSchema,
        color_scheme: ColorScheme,
    ):
        self.ctx = ctx
        self.schema = schema

        self.color_scheme = color_scheme
        self.simulation_time = 0.0
        self.setting_history: dict[str, deque[float]] = {}
        self.metric_history: dict[str, deque[float]] = {}
        self.history_times: deque[float] = deque(maxlen=self.HISTORY_LIMIT)
        self.metric_history_times = self.history_times
        self._data_collection_accumulator = 0.0
        self.history_revision = 0
        self.simulation_name = type(self).__module__.rsplit(".", 1)[-1]

    @classmethod
    def get_schema(cls) -> SettingsSchema:
        return {
            "simulation_speed": SliderDetails(
                "Simulation Speed",
                initial_only=False,
                setting=cls.SIMULATION_SPEED,
                lower_bound=0.1,
                upper_bound=10.0
            ),
            "record_csv": CheckboxDetails(
                "Record Gathered Data",
                initial_only=True,
                setting=cls.RECORD_CSV,
                initial_value=False
            ),
            "csv_filename": InputDetails(
                "CSV Output Name",
                initial_only=True,
                setting=cls.CSV_FILENAME,
                placeholder_text="Enter a name"
            )
        }

    def process_mouse(
        self,
        dx: int,
        dy: int,
        scroll_dy: int,
        *,
        panning: bool = False,
        mouse_pos: tuple[int, int] | None = None,
        frame_rect: pygame.Rect | None = None,
    ):
        pass

    @property
    def simulation_speed(self) -> float:
        return float(self.schema["simulation_speed"].setting.value)  # type: ignore

    def step(self, dt: float) -> None:
        pass

    def advance(self, dt: float) -> None:
        self.step(dt)
        self.simulation_time += dt
        interval_details = self.schema.get("data_collection_interval")
        if interval_details is None:
            interval = self.DEFAULT_DATA_COLLECTION_INTERVAL
        elif isinstance(interval_details, SliderDetails):
            interval = float(interval_details.setting.value)
        else:
            raise TypeError("Data collection interval must be a slider setting.")
        interval = max(interval, 1e-6)
        self._data_collection_accumulator += max(dt, 0.0)
        if self._data_collection_accumulator < interval:
            return

        self._data_collection_accumulator %= interval
        self.history_times.append(self.simulation_time)
        for name, details in self.schema.items():
            if details.initial_only or isinstance(details, (CompoundDetails, ListDetails)):
                continue

            if isinstance(details, SliderDetails):
                value: bool | int | float | str = details.setting.value
            elif isinstance(details, CheckboxDetails):
                value = details.setting.value
            elif isinstance(details, DropdownDetails):
                value = details.setting.value
            elif isinstance(details, InputDetails):
                value = cast(InputDetails[Any], details).setting.value
            else:
                continue
            if isinstance(value, bool):
                history = self.setting_history.setdefault(
                    details.name,
                    deque(maxlen=self.HISTORY_LIMIT),
                )
                history.append(float(value))
            elif isinstance(value, (int, float)) and isinstance(details, SliderDetails):
                lower_bound = float(details.lower_bound)
                upper_bound = float(details.upper_bound)
                normalized_value = (
                    0.0
                    if upper_bound == lower_bound
                    else (float(value) - lower_bound) / (upper_bound - lower_bound)
                )
                history = self.setting_history.setdefault(
                    details.name,
                    deque(maxlen=self.HISTORY_LIMIT),
                )
                history.append(min(max(normalized_value, 0.0), 1.0))

        metrics = self.get_metrics()
        for name in tuple(self.metric_history):
            if name not in metrics:
                del self.metric_history[name]
        for name, value in metrics.items():
            self.metric_history.setdefault(
                name,
                deque(maxlen=self.HISTORY_LIMIT),
            ).append(float(value))
        self.history_revision += 1

    def get_metrics(self) -> dict[str, float]:
        return {}

    def get_metric_series(self) -> dict[str, list[float]]:
        return {
            name: list(values)
            for name, values in self.metric_history.items()
        }

    def get_setting_series(self) -> dict[str, list[float]]:
        return {
            details.name: list(self.setting_history[details.name])
            for details in self.schema.values()
            if (
                not details.initial_only
                and details.name in self.setting_history
            )
        }

    def export_csv(self) -> Path | None:
        record_details = self.schema.get("record_csv")
        filename_details = self.schema.get("csv_filename")
        if record_details is None or filename_details is None:
            return None
        if not isinstance(record_details, CheckboxDetails):
            raise TypeError("CSV recording must be controlled by a checkbox.")
        if not isinstance(filename_details, InputDetails):
            raise TypeError("CSV filename must be an input setting.")
        if not record_details.setting.value:
            return None

        filename_value = cast(InputDetails[Any], filename_details).setting.value
        filename = Path(str(filename_value).strip()).name
        if not filename or filename in {".", ".."}:
            raise ValueError("CSV filename must not be empty.")
        if Path(filename).suffix.lower() != ".csv":
            filename += ".csv"

        readings_dir = self.READINGS_ROOT / self.simulation_name
        readings_dir.mkdir(parents=True, exist_ok=True)
        output_path = readings_dir / filename

        data: dict[str, list[float]] = {
            "Simulation time (s)": list(self.history_times),
        }
        data.update(self.get_setting_series())
        data.update(self.get_metric_series())
        pd.DataFrame(data).to_csv(output_path, index=False)
        return output_path

    def render(self, surf: pygame.Surface, frame_rect: pygame.Rect | None = None) -> None:
        raise NotImplementedError

    def cleanup(self) -> None:
        self.export_csv()
