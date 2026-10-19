import unittest

import pygame

from src.engine.ui.components.dropdown import Dropdown
from src.engine.ui.components.input import Input
from src.engine.ui.components.slider import Slider


class TestControlAccents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_input_uses_accent_border_while_active(self):
        font = pygame.font.Font(None, 16)
        control = Input(
            (0, 0),
            100,
            font,
            accent_color=(255, 128, 0),
            border_color=(20, 20, 20),
        )
        self.assertEqual(control.rect.width, 100)
        self.assertEqual(
            control.rect.height,
            font.get_linesize() + 2 * control.PADDING_Y,
        )
        control.rect.topleft = (10, 10)
        control.is_active = True
        surface = pygame.Surface((120, 50))

        control.draw(surface)

        self.assertEqual(surface.get_at((10, 20))[:3], (255, 128, 0))

    def test_slider_uses_accent_on_handle_while_hovered(self):
        control = Slider(
            (0, 0),
            width=100,
            initial_value=0.5,
            accent_color=(255, 128, 0),
            border_color=(20, 20, 20),
        )
        control.rect.topleft = (10, 10)
        control.is_hovered = True
        surface = pygame.Surface((120, 50))

        control.draw(surface)

        self.assertEqual(surface.get_at((10, 16))[:3], (20, 20, 20))
        self.assertEqual(surface.get_at((60, 10))[:3], (255, 128, 0))

    def test_dropdown_hover_darkens_option_and_uses_normal_menu_border(self):
        control = Dropdown(
            (0, 0),
            min_width=100,
            options=("One", "Two"),
            placeholder_text="Choose",
            font=pygame.font.Font(None, 16),
            border_color=(20, 20, 20),
            accent_color=(255, 128, 0),
        )
        control.rect.topleft = (10, 10)
        control.is_open = True
        control.hovered_option = 0
        surface = pygame.Surface((120, 120))

        control.draw(surface)

        self.assertEqual(surface.get_at((10, 10))[:3], (255, 128, 0))
        option_y = control.rect.bottom + 3
        self.assertEqual(surface.get_at((20, option_y))[:3], (22, 22, 22))
        self.assertEqual(surface.get_at((10, option_y))[:3], (20, 20, 20))

    def test_dropdown_keeps_opaque_background(self):
        control = Dropdown(
            (0, 0),
            min_width=100,
            options=("One",),
            placeholder_text="Choose",
            font=pygame.font.Font(None, 16),
            background_color=(200, 100, 50),
            border_color=(20, 20, 20),
        )
        control.rect.topleft = (10, 10)
        surface = pygame.Surface((120, 80), pygame.SRCALPHA)

        control.draw(surface)

        self.assertEqual(surface.get_at((70, 20)), pygame.Color(200, 100, 50, 255))
        self.assertEqual(surface.get_at((6, 20)).a, 0)

    def test_dropdown_default_background_is_opaque(self):
        control = Dropdown(
            (0, 0),
            min_width=100,
            options=(),
            placeholder_text="Choose",
            font=pygame.font.Font(None, 16),
        )
        control.rect.topleft = (10, 10)
        surface = pygame.Surface((120, 80), pygame.SRCALPHA)

        control.draw(surface)

        self.assertEqual(surface.get_at((70, 20)), pygame.Color(30, 30, 30, 255))
        self.assertEqual(surface.get_at((6, 20)).a, 0)

    def test_dropdown_reuses_rendered_option_text(self):
        control = Dropdown(
            (0, 0),
            min_width=100,
            options=("One", "Two"),
            placeholder_text="Choose",
            font=pygame.font.Font(None, 16),
        )
        control.is_open = True
        surface = pygame.Surface((120, 120))

        control.draw(surface)
        cached_surfaces = tuple(control._text_surface_cache.values())
        control.draw(surface)

        self.assertEqual(len(control._text_surface_cache), 3)
        self.assertEqual(
            tuple(control._text_surface_cache.values()),
            cached_surfaces,
        )

    def test_dropdown_starts_at_its_default_value(self):
        control = Dropdown(
            (0, 0),
            min_width=100,
            options=("One", "Two"),
            placeholder_text="Choose",
            font=pygame.font.Font(None, 16),
            default_value="Two",
        )

        self.assertEqual(control.value, "Two")

    def test_dropdown_sizes_to_longest_text_and_font_height(self):
        font = pygame.font.Font(None, 16)
        options = ("Short", "An option wider than the minimum")
        control = Dropdown(
            (0, 0),
            min_width=10,
            options=options,
            placeholder_text="Pick",
            font=font,
        )

        widest_text = max(font.size(text)[0] for text in (*options, "Pick"))
        tallest_text = max(font.size(text)[1] for text in (*options, "Pick"))
        self.assertEqual(
            control.rect.width,
            widest_text + 2 * control.PADDING_X + control.ARROW_WIDTH,
        )
        self.assertEqual(
            control.rect.height,
            tallest_text + 2 * control.PADDING_Y,
        )


if __name__ == "__main__":
    unittest.main()
