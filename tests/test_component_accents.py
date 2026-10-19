import unittest

import pygame

from src.engine.ui.components.buttons import Button
from src.engine.ui.components.checkbox import Checkbox
from src.engine.ui.component import Component
from src.engine.ui.components.frame import Frame


class TestComponentAccents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_button_hover_changes_border_and_strengthens_text_only(self):
        button = Button(
            (0, 0),
            100,
            pygame.font.Font(None, 18),
            "Test",
            color=(100, 100, 100),
            background_color=(20, 20, 20),
            hover_color=(255, 0, 0),
            hover_text_color=(255, 255, 255),
            border_color=(40, 40, 40),
        )
        button.rect.topleft = (10, 10)
        surface = pygame.Surface((120, 60))

        button.draw(surface)
        self.assertEqual(surface.get_at((50, 10))[:3], (40, 40, 40))
        self.assertEqual(surface.get_at((50, 20))[:3], (20, 20, 20))
        self.assertEqual(button.label.color(), (100, 100, 100))

        button.is_hovered = True
        button.draw(surface)
        self.assertEqual(surface.get_at((50, 10))[:3], (255, 0, 0))
        self.assertEqual(surface.get_at((50, 20))[:3], (20, 20, 20))
        self.assertEqual(button.label.color(), (255, 255, 255))

    def test_button_sizes_to_label_and_updates_dynamic_text(self):
        font = pygame.font.Font(None, 18)
        text = ["Short"]
        button = Button((0, 0), 100, font, lambda: text[0])

        self.assertEqual(
            button.rect.size,
            (
                max(100, button.label.text_surf.get_width() + 2 * button.PADDING_X),
                button.label.text_surf.get_height() + 2 * button.PADDING_Y,
            ),
        )

        text[0] = "A much wider button label"
        button._update_size()
        self.assertEqual(
            button.rect.width,
            max(100, button.label.text_surf.get_width() + 2 * button.PADDING_X),
        )

    def test_checkbox_uses_accent_for_hover_and_check(self):
        checkbox = Checkbox(
            (0, 0),
            (20, 20),
            initial_value=True,
            accent_color=(255, 128, 0),
        )
        checkbox.rect.topleft = (10, 10)
        surface = pygame.Surface((40, 40))

        checkbox.draw(surface)

        self.assertEqual(surface.get_at((15, 10))[:3], (255, 128, 0))
        self.assertEqual(surface.get_at((15, 15))[:3], (255, 128, 0))

    def test_frame_resolves_accent_color_for_border(self):
        frame = Frame(
            (0, 0),
            20,
            accent_color=lambda: (255, 128, 0),
        )
        parent = Component((0, 0), (20, 20))
        parent.add_child(frame)
        frame.rect.topleft = (10, 10)
        surface = pygame.Surface((40, 40))

        frame.draw(surface)

        self.assertEqual(surface.get_at((10, 15))[:3], (255, 128, 0))


if __name__ == "__main__":
    unittest.main()
