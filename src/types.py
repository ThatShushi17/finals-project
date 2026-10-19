import pygame
from typing import Any
from collections.abc import Callable

from .settings import SettingDetails

type Dual = tuple[int, int]
type Dualf = tuple[float, float]

type Quad = tuple[int, int, int, int]
type Quadf = tuple[float, float, float, float]

type Colorlike = (
    tuple[int, int, int] |
    tuple[int, int, int, int] |
    str |
    pygame.Color
)

type FiendCallback = Callable[[], Any]
type SettingsSchema = dict[str, SettingDetails]
