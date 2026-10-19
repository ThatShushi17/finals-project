import unittest
from types import SimpleNamespace

import pygame

from src.engine.ui.component import Component
from src.engine.ui.components.frame import Frame
from src.engine.simulation.two.simulation_2d import Simulation2D


def make_frame_data(**values):
    from src.engine.frame_data import FrameData

    frame_data = object.__new__(FrameData)
    frame_data.__dict__.update(values)
    frame_data.consumed_events = set()
    return frame_data


def make_frame(simulation, height=80):
    parent = Component((0, 0), (100, height))
    frame = Frame((0, 0), height, simulation=simulation)  # type: ignore[arg-type]
    parent.add_child(frame)
    return frame


class RecordingSimulation:
    def __init__(self):
        self.frame_rect = None
        self.mouse_calls = []
        self.simulation_speed = 1.0
        self.step_calls = []

    def render(self, surf: pygame.Surface, frame_rect: pygame.Rect | None = None):
        self.frame_rect = frame_rect

    def process_mouse(
        self,
        dx: int,
        dy: int,
        scroll_dy: int,
        *,
        panning: bool = False,
        mouse_pos: tuple[int, int] | None = None,
        frame_rect: pygame.Rect | None = None,
    ):
        self.mouse_calls.append((dx, dy, scroll_dy, panning, mouse_pos, frame_rect))

    def step(self, dt: float):
        self.step_calls.append(dt)

    def advance(self, dt: float):
        self.step(dt)


class TestFrameRender(unittest.TestCase):
    def test_frame_scales_elapsed_time_by_simulation_speed(self):
        simulation = RecordingSimulation()
        simulation.simulation_speed = 2.5
        frame = make_frame(simulation)
        frame_data = make_frame_data(
            mouse_pos=(200, 200),
            events=[],
            dt=0.02,
        )

        frame._on_update(frame_data)

        self.assertEqual(simulation.step_calls, [0.05])

    def test_simulation_gets_frame_local_render_rectangle(self):
        simulation = RecordingSimulation()
        frame = make_frame(simulation)
        frame.rect.topleft = (120, 90)

        frame.draw(pygame.Surface((400, 300)))

        self.assertEqual(simulation.frame_rect, pygame.Rect(0, 0, 100, 80))

    def test_left_button_drag_is_forwarded_as_panning(self):
        simulation = RecordingSimulation()
        frame = make_frame(simulation)
        frame.rect.topleft = (20, 20)
        frame_data = make_frame_data(
            mouse_pos=(40, 40),
            events=[pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1)],
            dt=1 / 60,
        )

        frame._on_update(frame_data)
        frame_data.events = [
            pygame.event.Event(pygame.MOUSEMOTION, rel=(8, -5))
        ]
        frame._on_update(frame_data)

        self.assertEqual(
            simulation.mouse_calls,
            [(8, -5, 0, True, (20, 20), pygame.Rect(0, 0, 100, 80))],
        )

    def test_mouse_wheel_passes_frame_local_cursor_position(self):
        simulation = RecordingSimulation()
        frame = make_frame(simulation)
        frame.rect.topleft = (20, 30)
        wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
        frame_data = make_frame_data(
            mouse_pos=(45, 50),
            events=[wheel_event],
            dt=1 / 60,
        )

        frame._on_update(frame_data)

        self.assertEqual(
            simulation.mouse_calls,
            [(0, 0, 1, False, (25, 20), pygame.Rect(0, 0, 100, 80))],
        )
        self.assertTrue(frame_data.is_event_consumed(wheel_event))

    def test_simulation_2d_applies_camera_delta_when_panning(self):
        simulation = object.__new__(Simulation2D)
        simulation.camera_x = 10.0
        simulation.camera_y = 20.0
        simulation.zoom = 2.0

        simulation.process_mouse(8, -4, 0, panning=True)

        self.assertEqual(simulation.camera_x, 6.0)
        self.assertEqual(simulation.camera_y, 22.0)

    def test_zoom_keeps_cursor_world_position_fixed(self):
        simulation = object.__new__(Simulation2D)
        simulation.camera_x = 10.0
        simulation.camera_y = 20.0
        simulation.zoom = 2.0
        frame_rect = pygame.Rect(0, 0, 100, 80)
        cursor = (25, 15)
        world_before = simulation.screen_to_world(*cursor, frame_rect)

        simulation.process_mouse(
            0,
            0,
            1,
            mouse_pos=cursor,
            frame_rect=frame_rect,
        )

        world_after = simulation.screen_to_world(*cursor, frame_rect)
        self.assertAlmostEqual(world_before[0], world_after[0])
        self.assertAlmostEqual(world_before[1], world_after[1])

    def test_frame_width_tracks_parent_inner_width(self):
        simulation = RecordingSimulation()
        parent = Component((0, 0), (320, 100))
        frame = Frame((0, 0), 80, simulation=simulation)  # type: ignore[arg-type]
        parent.add_child(frame)

        self.assertEqual(frame.rect.width, 320)

        parent.rect.width = 480
        frame.update(make_frame_data(mouse_pos=(0, 0), events=[], dt=0))

        self.assertEqual(frame.rect.width, 480)


if __name__ == "__main__":
    unittest.main()
