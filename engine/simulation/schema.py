from dataclasses import dataclass
from typing import Any, List

@dataclass
class SimParameter:
    name: str
    label: str
    default: Any

@dataclass
class SliderParam(SimParameter):
    min_val: float
    max_val: float
    is_int: bool = False

@dataclass
class CheckboxParam(SimParameter):
    default: bool

@dataclass
class TextParam(SimParameter):
    default: str

class SimulationSchema:
    def __init__(self, parameters: List[SimParameter]):
        self.parameters = parameters

    def get_defaults(self) -> dict:
        """Extracts the default values into a dictionary."""
        return {param.name: param.default for param in self.parameters}