import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from src.engine.ui.components.buttons import Button
from src.engine.ui.components.plot import Plot
from src.engine.ui.menu_system import MenuSystem
from src.engine.ui.ui_builder import UIBuilder
from src.enums import TabStyles


def walk(component):
    yield component
    for child in component.children:
        yield from walk(child)


class TestGraphBrowser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def make_builder(self):
        font = pygame.font.Font(None, 18)
        font_handler = SimpleNamespace(
            default_size=18,
            get_font=lambda: font,
            get_heading=lambda: font,
        )
        color_scheme = SimpleNamespace(
            bg=lambda: (0, 0, 0),
            bg_bold=lambda: (20, 20, 20),
            fg_bold=lambda: (255, 255, 255),
            fg=lambda: (200, 200, 200),
            fg_hover=lambda: (255, 255, 255),
            bg_border=lambda: (40, 40, 40),
            accent=lambda _accent: (100, 100, 255),
        )
        frame_data = SimpleNamespace(window_size=(1000, 800))
        menu = MenuSystem(frame_data, font_handler, color_scheme, (1000, 800))
        return UIBuilder(menu, None), menu

    def find_buttons(self, tab):
        return [
            component
            for component in walk(tab)
            if isinstance(component, Button)
        ]

    def settle_transition(self, handler):
        frame_data = SimpleNamespace(
            window_size=(1000, 800),
            window_resized=False,
            mouse_pos=(0, 0),
            events=[],
            dt=0,
            is_event_consumed=lambda _event: False,
            consume_event=lambda _event: None,
        )
        start_time = next(iter(handler._transitions.values()))[2]
        with patch(
            "pygame.time.get_ticks",
            return_value=start_time + handler.TRANSITION_DURATION_MS,
        ):
            handler.update(frame_data)

    def test_graph_browser_lists_simulations_and_recordings_without_transitions(self):
        builder, menu = self.make_builder()
        handler = menu.tab_handler
        main_tab = menu.new_tab(TabStyles.ONE_CONTAINER, "Main")
        handler.push(main_tab)

        with tempfile.TemporaryDirectory() as directory:
            readings = Path(directory)
            ising_directory = readings / "ising"
            ising_directory.mkdir()
            (ising_directory / "run_one.csv").write_text(
                "Simulation time (s),Simulation Speed,Temperature,Magnetization,Energy / site\n"
                "0.1,0.5,0.4,0.2,-1.0\n",
                encoding="utf-8",
            )
            (ising_directory / "ignore.txt").write_text("ignored", encoding="utf-8")
            (readings / "reaction_diffusion").mkdir()

            builder._readings_directory = lambda: readings
            with patch("pygame.time.get_ticks", return_value=0):
                builder._open_view_graphs(main_tab)
            self.assertTrue(handler._transitions)
            self.settle_transition(handler)
            listing_tab = handler._active[-1]

            self.assertEqual(handler._transitions, {})
            buttons = self.find_buttons(listing_tab)
            self.assertEqual(
                [button.label.text_source for button in buttons],
                ["Ising", "Reaction Diffusion", "Back"],
            )

            buttons[0].callback()
            recordings_tab = handler._active[-1]
            self.assertEqual(handler._transitions, {})
            recording_buttons = self.find_buttons(recordings_tab)
            self.assertEqual(
                [button.label.text_source for button in recording_buttons],
                ["Run One", "Back"],
            )

            recording_buttons[0].callback()
            detail_tab = handler._active[-1]
            self.assertTrue(handler._transitions)
            self.settle_transition(handler)
            plots = [
                component for component in walk(detail_tab)
                if isinstance(component, Plot)
            ]
            self.assertEqual(len(plots), 2)
            self.assertEqual(plots[0].ax.get_title(), "Ising metrics")
            self.assertEqual(
                [line.get_label() for line in plots[0].ax.lines],
                ["Magnetization", "Energy / site"],
            )
            self.assertEqual(plots[1].ax.get_title(), "Settings over time")
            self.assertEqual(
                [line.get_label() for line in plots[1].ax.lines],
                ["Simulation Speed", "Temperature"],
            )

            detail_back = self.find_buttons(detail_tab)[0]
            with patch("pygame.time.get_ticks", return_value=700):
                detail_back.callback()
            self.settle_transition(handler)
            self.assertIs(handler._active[-1], recordings_tab)
            self.assertEqual(handler._transitions, {})

            recording_back = self.find_buttons(recordings_tab)[-1]
            recording_back.callback()
            self.assertIs(handler._active[-1], listing_tab)
            self.assertEqual(handler._transitions, {})
            self.assertEqual(handler._history, [main_tab])

            listing_back = self.find_buttons(listing_tab)[-1]
            with patch("pygame.time.get_ticks", return_value=1300):
                listing_back.callback()
            self.assertTrue(handler._transitions)
            self.settle_transition(handler)
            self.assertIs(handler._active[-1], main_tab)

    def test_view_graphs_menu_is_recreated_when_opened(self):
        builder, menu = self.make_builder()
        main_tab = menu.new_tab(TabStyles.ONE_CONTAINER, "Main")
        menu.tab_handler.push(main_tab)

        with tempfile.TemporaryDirectory() as directory:
            readings = Path(directory)
            (readings / "ising").mkdir()
            builder._readings_directory = lambda: readings

            with patch("pygame.time.get_ticks", return_value=0):
                builder._open_view_graphs(main_tab)
            first_tab = menu.tab_handler._active[-1]
            self.settle_transition(menu.tab_handler)
            with patch("pygame.time.get_ticks", return_value=700):
                menu.tab_handler.reverse_shove()
            self.settle_transition(menu.tab_handler)
            with patch("pygame.time.get_ticks", return_value=700):
                builder._open_view_graphs(main_tab)
            second_tab = menu.tab_handler._active[-1]

        self.assertIsNot(first_tab, second_tab)
        self.assertTrue(menu.tab_handler._transitions)

    def test_delete_recording_removes_file_and_refreshes_recording_list(self):
        builder, menu = self.make_builder()
        handler = menu.tab_handler
        main_tab = menu.new_tab(TabStyles.ONE_CONTAINER, "Main")
        handler.push(main_tab)

        with tempfile.TemporaryDirectory() as directory:
            simulation_directory = Path(directory) / "ising"
            simulation_directory.mkdir()
            recording = simulation_directory / "run_one.csv"
            recording.write_text(
                "Simulation time (s),Simulation Speed,Temperature,Magnetization\n"
                "0.1,0.5,0.4,0.2\n",
                encoding="utf-8",
            )

            builder._open_recordings_menu(simulation_directory, main_tab)
            recordings_tab = handler._active[-1]
            self.find_buttons(recordings_tab)[0].callback()
            detail_tab = handler._active[-1]
            self.settle_transition(handler)
            detail_buttons = self.find_buttons(detail_tab)

            self.assertEqual(
                [button.label.text_source for button in detail_buttons],
                ["Delete Recording", "Back"],
            )
            with patch("pygame.time.get_ticks", return_value=700):
                detail_buttons[0].callback()

            self.assertFalse(recording.exists())
            self.settle_transition(handler)
            self.assertIs(handler._active[-1], recordings_tab)
            self.assertEqual(
                [button.label.text_source for button in self.find_buttons(recordings_tab)],
                ["Back"],
            )


if __name__ == "__main__":
    unittest.main()
