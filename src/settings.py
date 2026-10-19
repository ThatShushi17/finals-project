import pandas as pd
from pathlib import Path
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from .enums import Accents, InputTypes

T = TypeVar('T', str, int, float, bool)

@dataclass
class Setting(Generic[T]):
    value: T

@dataclass
class SettingDetails:
    name: str
    input_type: InputTypes
    initial_only: bool = False

@dataclass(kw_only=True)
class SliderDetails(SettingDetails):
    setting: Setting[int] | Setting[float]
    lower_bound: int | float
    upper_bound: int | float
    input_type: InputTypes = InputTypes.SLIDER

@dataclass(kw_only=True)
class InputDetails(SettingDetails, Generic[T]):
    setting: Setting[T]
    placeholder_text: str
    input_type: InputTypes = InputTypes.INPUT

    def __post_init__(self):
        self.numeric_only = isinstance(self.setting.value, int) or isinstance(self.setting.value, float)

@dataclass(kw_only=True)
class CheckboxDetails(SettingDetails):
    setting: Setting[bool]
    initial_value: bool
    input_type: InputTypes = InputTypes.CHECKBOX

@dataclass(kw_only=True)
class DropdownDetails(SettingDetails):
    setting: Setting[str]
    options: tuple[str, ...]
    placeholder_text: str
    default_value: str
    input_type: InputTypes = InputTypes.DROPDOWN

@dataclass(kw_only=True)
class PresetDetails(DropdownDetails):
    selection_callback: Callable[[str], None] = lambda _: None

@dataclass(kw_only=True)
class CompoundDetails(SettingDetails):
    details: dict[str, SettingDetails]
    accent: Accents | Callable[[], Accents] | None = None
    opacity: float = 0.4
    input_type: InputTypes = InputTypes.COMPOUND

@dataclass(kw_only=True)
class ListDetails(SettingDetails):
    details: list[SettingDetails]
    opacity: float = 0.4
    generation_callback: Callable[[], SettingDetails] = field(
        default_factory=lambda: lambda: InputDetails(
            name="Item",
            setting=Setting(""),
            placeholder_text="Enter a value",
        )
    )
    input_type: InputTypes = InputTypes.LIST

class Settings:
    def __init__(self, source: Path) -> None:
        self.themes = pd.read_csv(Path(__file__).resolve().parent.parent / "data" / "misc" / "themes.csv", index_col="name")
        
        self.source = source
        if source.is_file() and source.suffix == '.csv':
            df = pd.read_csv(source)
            self.fps = Setting[int](
                int(df.loc[0, "fps"])  # type: ignore
                if "fps" in df
                else 60
            )
            self.theme = Setting[str](
                str(df.loc[0, "theme"])
                if "theme" in df
                else "Default Dark"
            )
            self.data_collection_interval = Setting[float](
                float(df.loc[0, "data_collection_interval"])  # type: ignore
                if "data_collection_interval" in df
                else 0.1
            )
            return
        
        self.fps = Setting[int](60)
        self.theme = Setting[str]("Default Dark")
        self.data_collection_interval = Setting[float](0.1)
        self.write_csv()

    def write_csv(self):
        self.source.parent.mkdir(parents=True, exist_ok=True)
        
        df = pd.DataFrame([{
            "fps": self.fps.value,
            "theme": self.theme.value,
            "data_collection_interval": self.data_collection_interval.value,
        }])
        df.to_csv(self.source, index=False)

    def expose_schema(self) -> dict[str, SettingDetails]:
        return {
            "fps": SliderDetails(
                "FPS",
                setting=self.fps,
                lower_bound=15,
                upper_bound=144
            ),
            "data_collection_interval": SliderDetails(
                "Data Collection Interval (seconds)",
                setting=self.data_collection_interval,
                lower_bound=0.1,
                upper_bound=5.0,
            ),
            "theme": DropdownDetails(
                "Theme",
                setting=self.theme,
                options=tuple(self.themes.index),
                placeholder_text="Select theme",
                default_value=self.theme.value,
            )
        }