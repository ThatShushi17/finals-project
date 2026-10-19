import unittest
from types import SimpleNamespace

import pygame

from src.engine.ui.components.buttons import Button
from src.engine.ui.component import Component
from src.engine.ui.components.frame import Frame
from src.engine.ui.components.input import Input


def make_frame_data(**values):
    from src.engine.frame_data import FrameData

    frame_data = object.__new__(FrameData)
    frame_data.__dict__.update(values)
    frame_data.consumed_events = set()
    return frame_data


class TestInputEventHandling(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def test_clicking_button_outside_input_does_not_consume_click(self):
        event = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)
        frame_data = make_frame_data(
            events=[event],
            mouse_pos=(150, 20),
        )
        input_component = Input((0, 0), 80, pygame.font.Font(None, 16))
        input_component.rect.topleft = (0, 0)
        launched: list[bool] = []
        button = Button(
            (0, 0),
            200,
            pygame.font.Font(None, 16),
            "Launch",
            callback=lambda: launched.append(True),
        )
        button.rect.topleft = (100, 0)

        input_component._on_update(frame_data)
        button._on_update(frame_data)

        self.assertEqual(launched, [True])
        self.assertTrue(frame_data.is_event_consumed(event))

    def test_clicking_input_still_consumes_click(self):
        event = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)
        frame_data = make_frame_data(
            events=[event],
            mouse_pos=(40, 20),
        )
        input_component = Input((0, 0), 80, pygame.font.Font(None, 16))
        input_component.rect.topleft = (0, 0)
        launched: list[bool] = []
        button = Button(
            (0, 0),
            200,
            pygame.font.Font(None, 16),
            "Launch",
            callback=lambda: launched.append(True),
        )
        button.rect.topleft = (0, 0)

        input_component._on_update(frame_data)
        button._on_update(frame_data)

        self.assertTrue(input_component.is_active)
        self.assertTrue(frame_data.is_event_consumed(event))
        self.assertEqual(launched, [])

    def test_consuming_scroll_does_not_consume_click_in_same_frame(self):
        wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
        click_event = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)
        frame_data = make_frame_data(
            events=[wheel_event, click_event],
            mouse_pos=(20, 20),
            dt=1 / 60,
        )
        simulation = SimpleNamespace(
            mouse_calls=[],
            simulation_speed=1.0,
            process_mouse=lambda *args, **kwargs: simulation.mouse_calls.append(args),
            advance=lambda _: None,
        )
        parent = Component((0, 0), (100, 40))
        frame = Frame((0, 0), 40, simulation=simulation)
        parent.add_child(frame)
        frame.rect.topleft = (0, 0)
        launched: list[bool] = []
        button = Button(
            (0, 0),
            100,
            pygame.font.Font(None, 16),
            "Launch",
            callback=lambda: launched.append(True),
        )
        button.rect.topleft = (0, 0)

        frame._on_update(frame_data)
        button._on_update(frame_data)

        self.assertTrue(frame_data.is_event_consumed(wheel_event))
        self.assertTrue(frame_data.is_event_consumed(click_event))
        self.assertEqual(simulation.mouse_calls[0][2], 1)
        self.assertEqual(launched, [True])


if __name__ == "__main__":
    unittest.main()
