import unittest

import pygame

from src.engine.ui.components.tabs import _prepare_hex_image
from src.engine.ui.images import HEX_IMAGE, load_cover_image
from src.enums import HexFadeCorner


class TestHexBackground(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    def test_cover_loader_preserves_png_alpha(self):
        image = load_cover_image(HEX_IMAGE, (1536, 1024))
        alpha = pygame.surfarray.array_alpha(image)

        self.assertEqual(int(alpha.min()), 0)
        self.assertEqual(int(alpha.max()), 255)

    def test_hex_tint_is_visible_near_entry_corner_and_fades_outward(self):
        image = pygame.Surface((100, 100), pygame.SRCALPHA)
        image.fill((255, 0, 0, 255))
        accent = pygame.Color(106, 73, 255)

        result = _prepare_hex_image(image, accent, HexFadeCorner.BOTTOM_LEFT)

        self.assertEqual(result.get_at((0, 99))[:3], (accent.r, accent.g, accent.b))
        self.assertEqual(result.get_at((0, 99)).a, 255)
        self.assertEqual(result.get_at((10, 89)).a, 255)
        self.assertGreater(result.get_at((40, 59)).a, 0)
        self.assertLess(result.get_at((40, 59)).a, 255)
        self.assertEqual(result.get_at((99, 0)).a, 0)

    def test_hex_pattern_fades_from_selected_corner(self):
        accent = pygame.Color(106, 73, 255)
        corner_by_fade = {
            HexFadeCorner.TOP_LEFT: (0, 0),
            HexFadeCorner.TOP_RIGHT: (99, 0),
            HexFadeCorner.BOTTOM_LEFT: (0, 99),
            HexFadeCorner.BOTTOM_RIGHT: (99, 99),
        }

        for fade_corner, visible_corner in corner_by_fade.items():
            with self.subTest(fade_corner=fade_corner):
                image = pygame.Surface((100, 100), pygame.SRCALPHA)
                image.fill((255, 0, 0, 255))

                result = _prepare_hex_image(image, accent, fade_corner)

                self.assertEqual(result.get_at(visible_corner).a, 255)


if __name__ == "__main__":
    unittest.main()
