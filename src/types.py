import pygame

type Dual = tuple[int, int]
type Dualf = tuple[float, float]
type Colorlike = (
    tuple[int, int, int] |
    tuple[int, int, int, int] |
    str |
    pygame.Color
)