import math
import pygame
from pathlib import Path

ARTEMIS_IMAGE = Path(__file__).resolve().parent.parent.parent.parent / "assets/images/artemis.jpg"
HEX_IMAGE = Path(__file__).resolve().parent.parent.parent.parent / "assets/images/hex_grid.png"


def load_cover_image(path: Path, size: tuple[int, int]) -> pygame.Surface:
    """Scale an image to cover the target size without distortion."""
    image = pygame.image.load(path).convert_alpha()
    width, height = size

    scale = max(width / image.get_width(), height / image.get_height())
    scaled = pygame.transform.smoothscale(
        image,
        (
            math.ceil(image.get_width() * scale),
            math.ceil(image.get_height() * scale),
        ),
    )

    x = (scaled.get_width() - width) // 2
    y = (scaled.get_height() - height) // 2

    return scaled.subsurface((x, y, width, height)).copy()
