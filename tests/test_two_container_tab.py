import unittest
from types import SimpleNamespace

import pygame

from src.engine.ui.menu_system import MenuSystem
from src.engine.ui.components.container import Container
from src.enums import Accents, Cardinal, HexFadeCorner, TabBackgrounds, TabStyles
from src.settings import CheckboxDetails, Setting


def make_frame_data(**values):
    from src.engine.frame_data import FrameData

    frame_data = object.__new__(FrameData)
    frame_data.__dict__.update(values)
    frame_data.consumed_events = set()
    return frame_data


class TestTwoContainerTab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_settings_and_buttons_are_attached_to_side_by_side_columns(self):
        font = pygame.font.Font(None, 22)
        font_handler = SimpleNamespace(
            default_size=22,
            get_font=lambda: font,
            get_heading=lambda: font,
        )
        color_scheme = SimpleNamespace(
            bg=lambda: "#000000",
            bg_bold=lambda: "#111111",
            fg_bold=lambda: "#ffffff",
            fg=lambda: "#dddddd",
            fg_hover=lambda: "#ffffff",
            bg_border=lambda: "#080808",
            accent=lambda _: "#00ff00",
        )
        frame_data = SimpleNamespace(window_size=(1600, 900))
        menu = MenuSystem(frame_data, font_handler, color_scheme, (1600, 900))

        tab = menu.new_tab(
            TabStyles.TWO_CONTAINERS,
            "Configure Simulation",
            background=TabBackgrounds.HEX,
            accent=Accents.ORANGE,
            hex_fade_corner=HexFadeCorner.TOP_RIGHT,
        )
        self.assertIs(tab.home, Cardinal.BOTTOM)
        self.assertIs(tab.hex_fade_corner, HexFadeCorner.TOP_RIGHT)
        self.assertIs(tab.background[0], TabBackgrounds.HEX)
        left_column, right_column = tab.containers
        self.assertEqual(left_column.scrollbar_handle_color(), "#ffffff")
        self.assertEqual(left_column.scrollbar_accent_color(), "#00ff00")
        self.assertEqual(left_column.scrollbar_track_color(), "#dddddd")
        menu.add_settings_from_schema(
            left_column,
            {
                "enabled": CheckboxDetails(
                    "Enabled",
                    setting=Setting(False),
                    initial_value=False,
                )
            },
        )
        menu.add_button_list(
            right_column,
            ("Launch Simulation", lambda: None, Accents.GREEN),
            ("Back", lambda: None, Accents.PINK),
        )

        tab.update(
            make_frame_data(
                window_size=(1600, 900),
                window_resized=False,
                mouse_pos=(0, 0),
                events=[],
                dt=1 / 60,
            )
        )

        self.assertIsInstance(left_column.parent, Container)
        self.assertIs(left_column.parent, right_column.parent)
        self.assertLess(left_column.rect.right, right_column.rect.left)
        self.assertGreater(left_column.rect.width, 200)
        self.assertGreater(right_column.rect.width, 200)
        self.assertEqual(len(left_column.children), 2)
        self.assertEqual(len(right_column.children), 2)
        self.assertTrue(all(button.rect.left >= right_column.rect.left for button in right_column.children))


if __name__ == "__main__":
    unittest.main()
