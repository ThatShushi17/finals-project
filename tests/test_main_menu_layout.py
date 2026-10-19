import unittest
from types import SimpleNamespace

import pygame

from src.engine.ui.components.buttons import Button
from src.engine.ui.components.container import Container
from src.engine.ui.components.label import Label
from src.engine.ui.menu_system import MenuSystem
from src.engine.ui.ui_builder import UIBuilder
from src.enums import Alignment, Axis, Position


class TestMainMenuLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_main_menu_has_top_left_title_and_unboxed_bottom_button_row(self):
        base_font = pygame.font.Font(None, 22)
        font_handler = SimpleNamespace(
            default_size=22,
            get_font=lambda *_args, **_kwargs: base_font,
            get_bold=lambda size=None: pygame.font.Font(None, size or 22),
            get_heading=lambda: base_font,
        )
        color_scheme = SimpleNamespace(
            bg=lambda: pygame.Color("#000000"),
            bg_bold=lambda: pygame.Color("#111111"),
            fg_bold=lambda: pygame.Color("#ffffff"),
            fg=lambda: pygame.Color("#dddddd"),
            fg_hover=lambda: pygame.Color("#ffffff"),
            bg_border=lambda: pygame.Color("#080808"),
            accent=lambda _accent: pygame.Color("#00ff00"),
        )
        frame_data = SimpleNamespace(
            window_size=(1200, 800),
            window_resized=False,
            mouse_pos=(0, 0),
            events=[],
            dt=1 / 60,
            consumed_events=set(),
            is_event_consumed=lambda _event: False,
            consume_event=lambda _event: None,
        )
        menu = MenuSystem(frame_data, font_handler, color_scheme, (1200, 800))
        builder = UIBuilder(menu, None)
        settings = SimpleNamespace(expose_schema=lambda: {})

        builder.create_ui(lambda: None, settings)
        main_tab = menu.tab_handler._active[-1]
        main_tab.update(frame_data)

        title, button_row = main_tab.children
        self.assertIsInstance(title, Label)
        self.assertEqual(title.text_source, "Science Simulations")
        self.assertEqual(title.anchor, Position.TOP_CENTER)
        self.assertEqual(title.dock, Position.TOP_CENTER)
        self.assertEqual(title.rect.top, 72)
        self.assertEqual(title.rect.centerx, main_tab.rect.centerx)
        self.assertGreater(title.font.get_height(), base_font.get_height() * 2)

        self.assertIsInstance(button_row, Container)
        self.assertEqual(button_row.axis, Axis.HORIZONTAL)
        self.assertEqual(button_row.alignment, Alignment.SPACE_AROUND)
        self.assertIsNone(button_row.background_color)
        self.assertEqual(len(button_row.children), 4)
        buttons = button_row.children
        self.assertTrue(all(isinstance(button, Button) for button in buttons))
        self.assertTrue(all(button.rect.width >= 240 for button in buttons))
        self.assertTrue(all(
            first.rect.right < second.rect.left
            for first, second in zip(buttons, buttons[1:])
        ))
        self.assertGreater(button_row.rect.top, main_tab.rect.height // 2)
        self.assertLess(button_row.rect.bottom, main_tab.rect.bottom)


if __name__ == "__main__":
    unittest.main()
