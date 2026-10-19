import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from src.engine.ui.component import Component
from src.engine.ui.components.tabs import Tab, TabHandler
from src.enums import Cardinal, TabBackgrounds


class TestTabTransitions(unittest.TestCase):
    def make_tab(self):
        frame_data = SimpleNamespace(window_size=(100, 100))
        root = Component((0, 0), (100, 100))
        handler = TabHandler(root, frame_data)
        tab = Tab(
            handler,
            background_color=(255, 0, 0),
            home=Cardinal.BOTTOM,
            background=(TabBackgrounds.SOLID, (255, 0, 0)),
        )
        return handler, tab

    def test_background_moves_with_tab_offset(self):
        handler, tab = self.make_tab()
        child = Component((0, 0), (10, 10))
        tab.add_child(child)
        with patch("pygame.time.get_ticks", return_value=0):
            handler.open(tab)

        surface = pygame.Surface((100, 100))
        surface.fill((0, 255, 0))

        tab.draw(surface)

        self.assertEqual(surface.get_at((50, 50)), pygame.Color(0, 255, 0))
        self.assertEqual(child.offset, (0, 100))
        self.assertEqual(tab.rect.topleft, (0, 0))

    def test_transition_uses_ease_in_out_progress(self):
        handler, tab = self.make_tab()
        child = Component((0, 0), (10, 10))
        tab.add_child(child)
        with patch("pygame.time.get_ticks", return_value=0):
            handler.open(tab)

        self.assertEqual(child.offset, (0, 100))

        frame_data = SimpleNamespace(window_size=(100, 100), window_resized=False)
        with patch("pygame.time.get_ticks", side_effect=[0, 150, 300, 450, 600]):
            offsets = []
            for _ in range(5):
                handler.update(frame_data)
                offsets.append(tab.personal_offset[1])
                self.assertEqual(tab.rect.topleft, (0, 0))

        self.assertEqual(offsets, [100, 84, 50, 16, 0])
        self.assertEqual(handler._active, [tab])
        self.assertNotIn(tab, handler._transitions)

    def test_shove_moves_current_tab_up_and_opens_next_tab_from_below(self):
        handler, current = self.make_tab()
        next_tab = Tab(
            handler,
            background_color=(0, 0, 255),
            background=(TabBackgrounds.SOLID, (0, 0, 255)),
        )
        handler.push(current)

        with patch("pygame.time.get_ticks", return_value=0):
            handler.shove(next_tab)

        self.assertEqual(current.offset, (0, 0))
        self.assertEqual(next_tab.offset, (0, 100))
        self.assertEqual(handler._history, [current])

        frame_data = SimpleNamespace(window_size=(100, 100), window_resized=False)
        with patch("pygame.time.get_ticks", side_effect=[300, 600]):
            handler.update(frame_data)
            self.assertEqual(current.offset, (0, -50))
            self.assertEqual(next_tab.offset, (0, 50))
            handler.update(frame_data)

        self.assertEqual(handler._active, [next_tab])
        self.assertEqual(next_tab.offset, (0, 0))

    def test_reverse_shove_returns_to_previous_tab_in_reverse_direction(self):
        handler, previous = self.make_tab()
        current = Tab(
            handler,
            background_color=(0, 0, 255),
            background=(TabBackgrounds.SOLID, (0, 0, 255)),
        )
        handler.push(previous)
        with patch("pygame.time.get_ticks", return_value=0):
            handler.shove(current)

        frame_data = SimpleNamespace(window_size=(100, 100), window_resized=False)
        with patch("pygame.time.get_ticks", return_value=600):
            handler.update(frame_data)

        with patch("pygame.time.get_ticks", return_value=700):
            handler.reverse_shove()

        self.assertEqual(previous.offset, (0, -100))
        self.assertEqual(current.offset, (0, 0))

        with patch("pygame.time.get_ticks", side_effect=[1000, 1300]):
            handler.update(frame_data)
            self.assertEqual(previous.offset, (0, -50))
            self.assertEqual(current.offset, (0, 50))
            handler.update(frame_data)

        self.assertEqual(handler._active, [previous])
        self.assertEqual(previous.offset, (0, 0))
        self.assertEqual(handler._history, [])

    def test_open_and_close_preserve_shove_history_for_selection_back(self):
        handler, main = self.make_tab()
        selection = Tab(
            handler,
            background_color=(0, 255, 0),
            background=(TabBackgrounds.SOLID, (0, 255, 0)),
        )
        config = Tab(
            handler,
            background_color=(0, 0, 255),
            background=(TabBackgrounds.SOLID, (0, 0, 255)),
        )
        simulation = Tab(
            handler,
            background_color=(255, 255, 0),
            background=(TabBackgrounds.SOLID, (255, 255, 0)),
        )
        handler.push(main)

        with patch("pygame.time.get_ticks", return_value=0):
            handler.shove(selection)
        frame_data = SimpleNamespace(window_size=(100, 100), window_resized=False)
        with patch("pygame.time.get_ticks", return_value=600):
            handler.update(frame_data)

        with patch("pygame.time.get_ticks", return_value=700):
            handler.shove(config)
        with patch("pygame.time.get_ticks", return_value=1300):
            handler.update(frame_data)

        with patch("pygame.time.get_ticks", return_value=1400):
            handler.open(simulation)
        with patch("pygame.time.get_ticks", return_value=2000):
            handler.update(frame_data)

        self.assertEqual(handler._history, [main, selection])

        with patch("pygame.time.get_ticks", return_value=2100):
            handler.close_to(selection)
        self.assertEqual(handler._history, [main])
        self.assertEqual(selection.offset, (0, -100))
        self.assertEqual(simulation.offset, (0, 0))

        with patch("pygame.time.get_ticks", return_value=2700):
            handler.update(frame_data)

        self.assertEqual(handler._active, [selection])
        self.assertEqual(selection.offset, (0, 0))

        with patch("pygame.time.get_ticks", return_value=2800):
            handler.reverse_shove()

        self.assertEqual(main.offset, (0, -100))
        self.assertEqual(selection.offset, (0, 0))


if __name__ == "__main__":
    unittest.main()
