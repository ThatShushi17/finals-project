import unittest
from types import SimpleNamespace

import pygame

from src.engine.ui.component import Component
from src.engine.ui.components.container import Container
from src.engine.ui.components.frame import Frame
from src.engine.ui.components.input import Input
from src.engine.ui.components.label import Label
from src.engine.ui.components.plot import Plot
from src.enums import Alignment, Axis, Position


def make_frame_data(**values):
    from src.engine.frame_data import FrameData

    frame_data = object.__new__(FrameData)
    frame_data.__dict__.update(values)
    frame_data.consumed_events = set()
    return frame_data


class PaintedComponent(Component):
    def __init__(self, size: tuple[int, int], color: tuple[int, int, int]):
        super().__init__((0, 0), size)
        self.color = color

    def draw(self, surf: pygame.Surface):
        pygame.draw.rect(surf, self.color, self.rect)


class TestContainerLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()

    def make_container(
        self,
        size: tuple[int, int],
        axis: Axis = Axis.VERTICAL,
        alignment: Alignment = Alignment.CENTER,
    ) -> Container:
        root = Component((0, 0), size)
        container = Container(
            axis=axis,
            cross_length=size[0] if axis == Axis.VERTICAL else size[1],
            cross_percent=0,
            alignment=alignment,
        )
        root.add_child(container)
        return container

    def test_center_alignment_centers_stack_using_child_top_edges(self):
        container = self.make_container((400, 800))
        first = Component((0, 0), (100, 40))
        second = Component((0, 0), (100, 40))
        first.margin_after = 20

        container.add_child(first, second)

        self.assertEqual(first.rect.top, 350)
        self.assertEqual(second.rect.top, 410)

    def test_center_alignment_keeps_overflowing_stack_centered(self):
        container = self.make_container((400, 800))
        first = Component((0, 0), (100, 300))
        second = Component((0, 0), (100, 300))

        container.add_child(first, second)

        self.assertEqual(first.rect.top, 100)
        self.assertEqual(second.rect.top, 400)

    def test_end_alignment_places_stack_at_container_end(self):
        container = self.make_container((400, 800), alignment=Alignment.END)
        first = Component((0, 0), (100, 40))
        second = Component((0, 0), (100, 40))

        container.add_child(first, second)

        self.assertEqual(first.rect.top, 696)
        self.assertEqual(second.rect.top, 736)

    def test_space_between_distributes_remaining_space_between_children(self):
        container = self.make_container((400, 800), alignment=Alignment.SPACE_BETWEEN)
        first = Component((0, 0), (100, 40))
        second = Component((0, 0), (100, 40))

        container.add_child(first, second)

        self.assertEqual(first.rect.top, 24)
        self.assertEqual(second.rect.top, 736)

    def test_space_around_distributes_remaining_space_around_children(self):
        container = self.make_container((400, 800), alignment=Alignment.SPACE_AROUND)
        first = Component((0, 0), (100, 40))
        second = Component((0, 0), (100, 40))

        container.add_child(first, second)

        self.assertEqual(first.rect.top, 192)
        self.assertEqual(second.rect.top, 568)

    def test_horizontal_container_aligns_children_along_width(self):
        container = self.make_container((800, 400), axis=Axis.HORIZONTAL)
        first = Component((0, 0), (100, 40))
        second = Component((0, 0), (100, 40))

        container.add_child(first, second)

        self.assertEqual(first.rect.left, 300)
        self.assertEqual(second.rect.left, 400)

    def test_cross_padding_insets_right_anchored_children(self):
        container = self.make_container((200, 300))
        child = Component(
            (0, 0),
            (40, 30),
            anchor=Position.TOP_RIGHT,
            dock=Position.TOP_RIGHT,
        )

        container.add_child(child)

        self.assertEqual(child.rect.right, container.rect.right - container.cross_padding)

    def test_cross_padding_insets_bottom_anchored_horizontal_children(self):
        container = self.make_container((300, 200), axis=Axis.HORIZONTAL)
        child = Component(
            (0, 0),
            (30, 40),
            anchor=Position.BOTTOM_LEFT,
            dock=Position.BOTTOM_LEFT,
        )

        container.add_child(child)

        self.assertEqual(child.rect.bottom, container.rect.bottom - container.cross_padding)

    def test_fit_content_container_tracks_its_child_stack_height(self):
        root = Component((0, 0), (400, 800))
        container = Container(
            cross_length=360,
            cross_percent=0,
            alignment=Alignment.START,
            fit_content=True,
        )
        root.add_child(container)
        first = Component((0, 0), (200, 40))
        second = Component((0, 0), (200, 30))
        first.margin_after = 12

        container.add_child(first, second)

        self.assertEqual(
            container.rect.height,
            2 * container.SCROLL_PADDING + 40 + 12 + 30,
        )

    def test_background_color_draws_translucent_panel_with_symmetric_shadow(self):
        root = Component((0, 0), (100, 100))
        container = Container(
            cross_length=40,
            cross_percent=0,
            background_color=(200, 100, 50),
        )
        root.add_child(container)
        container.rect = pygame.Rect(30, 30, 40, 40)
        surface = pygame.Surface((100, 100), pygame.SRCALPHA)

        container.draw(surface)

        self.assertEqual(surface.get_at((40, 40)), pygame.Color(200, 100, 50, 204))
        self.assertGreater(surface.get_at((28, 40)).a, 0)
        self.assertEqual(surface.get_at((28, 40)).a, surface.get_at((71, 40)).a)
        self.assertEqual(surface.get_at((13, 40)).a, 0)

    def test_background_surfaces_are_reused_between_draws(self):
        root = Component((0, 0), (100, 100))
        container = Container(
            cross_length=40,
            cross_percent=0,
            background_color=(200, 100, 50),
        )
        root.add_child(container)
        container.rect = pygame.Rect(30, 30, 40, 40)
        surface = pygame.Surface((100, 100), pygame.SRCALPHA)

        container.draw(surface)
        shadow = container._background_shadow
        panel = container._background_panel
        container.draw(surface)

        self.assertIs(container._background_shadow, shadow)
        self.assertIs(container._background_panel, panel)

    def test_container_without_background_keeps_surface_untouched(self):
        root = Component((0, 0), (100, 100))
        container = Container(cross_length=40, cross_percent=0)
        root.add_child(container)
        container.rect = pygame.Rect(30, 30, 40, 40)
        surface = pygame.Surface((100, 100), pygame.SRCALPHA)

        container.draw(surface)

        self.assertEqual(surface.get_at((40, 40)).a, 0)

    def test_label_only_renders_when_text_or_color_changes(self):
        text = ["Initial"]
        label = Label(
            (0, 0),
            pygame.font.Font(None, 16),
            lambda: text[0],
            color=(255, 255, 255),
        )
        frame_data = make_frame_data()
        initial_surface = label.text_surf

        label._on_update(frame_data)
        self.assertIs(label.text_surf, initial_surface)

        text[0] = "Updated"
        label._on_update(frame_data)
        self.assertIsNot(label.text_surf, initial_surface)

    def test_input_placeholder_cache_tracks_placeholder_alpha(self):
        input_component = Input(
            (0, 0),
            80,
            pygame.font.Font(None, 16),
            placeholder_text="same",
        )
        surface = pygame.Surface((100, 50), pygame.SRCALPHA)

        input_component.draw(surface)
        placeholder_surface = input_component._cached_text_surface
        self.assertEqual(placeholder_surface.get_alpha(), 102)

        input_component.text = "same"
        input_component.draw(surface)
        self.assertIsNot(input_component._cached_text_surface, placeholder_surface)
        self.assertEqual(input_component._cached_text_surface.get_alpha(), 255)

    def test_overflow_layout_starts_at_top_independent_of_alignment(self):
        container = self.make_container((100, 100), alignment=Alignment.END)
        children = [Component((0, 0), (80, 40)) for _ in range(4)]

        container.add_child(*children)

        self.assertTrue(container.is_scrollable)
        self.assertEqual([child.rect.top for child in children], [24, 64, 104, 144])

    def test_mouse_wheel_scrolls_overflow_content(self):
        container = self.make_container((100, 100), alignment=Alignment.CENTER)
        children = [Component((0, 0), (80, 40)) for _ in range(4)]
        container.add_child(*children)
        frame_data = make_frame_data(
            mouse_pos=(20, 20),
            events=[pygame.event.Event(pygame.MOUSEWHEEL, y=-1)],
        )

        container.update(frame_data)

        self.assertEqual(container.scroll_offset, Container.SCROLL_STEP)
        self.assertEqual(children[0].rect.top, Container.SCROLL_PADDING - Container.SCROLL_STEP)
        self.assertTrue(frame_data.is_event_consumed(frame_data.events[0]))

    def test_horizontal_container_scrolls_along_its_main_axis(self):
        container = self.make_container(
            (100, 100),
            axis=Axis.HORIZONTAL,
            alignment=Alignment.END,
        )
        children = [Component((0, 0), (40, 80)) for _ in range(4)]
        container.add_child(*children)
        frame_data = make_frame_data(
            mouse_pos=(20, 20),
            events=[pygame.event.Event(pygame.MOUSEWHEEL, y=-1)],
        )

        container.update(frame_data)

        self.assertEqual([child.rect.left for child in children], [-16, 24, 64, 104])

    def test_scrollbar_uses_theme_track_and_handle_colors_and_clips_children(self):
        container = self.make_container((100, 100))
        container.scrollbar_handle_color = (240, 240, 240)
        container.scrollbar_accent_color = (255, 128, 0)
        container.scrollbar_track_color = (100, 120, 140)
        children = [
            PaintedComponent((100, 40), (0, 255, 0))
            for _ in range(4)
        ]
        container.add_child(*children)
        surface = pygame.Surface((100, 100), pygame.SRCALPHA)

        hover_data = make_frame_data(
            mouse_pos=(80, 28),
            events=[],
        )
        container.update(hover_data)
        container.draw(surface)

        self.assertEqual(surface.get_at((60, 28))[:3], (0, 255, 0))
        self.assertNotEqual(surface.get_at((80, 28))[:3], (0, 255, 0))
        self.assertEqual(surface.get_at((80, 28))[:3], (255, 128, 0))
        self.assertEqual(surface.get_at((80, 70)), pygame.Color(100, 120, 140, 153))
        self.assertNotEqual(surface.get_at((80, 90))[:3], (0, 255, 0))

        frame_data = make_frame_data(
            mouse_pos=(80, 28),
            events=[
                pygame.event.Event(
                    pygame.MOUSEBUTTONDOWN,
                    button=1,
                    pos=(80, 28),
                )
            ],
        )
        container.update(frame_data)
        surface.fill((0, 0, 0, 0))
        container.draw(surface)

        self.assertTrue(container.is_scrollbar_dragging)
        self.assertEqual(surface.get_at((80, 28))[:3], (255, 128, 0))

    def test_scrolled_content_is_clipped_above_container_top(self):
        root = Component((0, 0), (100, 100))
        container = Container(cross_length=100, cross_percent=0)
        root.add_child(container)
        container.rect = pygame.Rect(0, 20, 100, 100)
        children = [
            PaintedComponent((100, 40), (255, 0, 0)),
            PaintedComponent((100, 40), (0, 255, 0)),
            PaintedComponent((100, 40), (0, 0, 255)),
            PaintedComponent((100, 40), (255, 255, 0)),
        ]
        container.add_child(*children)
        container.scroll_offset = 64
        container.update_children_positions()
        surface = pygame.Surface((100, 140), pygame.SRCALPHA)

        container.draw(surface)

        self.assertEqual(children[0].rect.top, -20)
        self.assertEqual(surface.get_at((10, 50)).a, 0)
        self.assertEqual(surface.get_at((20, 10)).a, 0)
        self.assertEqual(surface.get_at((20, 50))[:3], (0, 255, 0))

    def test_scrollable_container_has_symmetric_main_axis_padding(self):
        container = self.make_container((100, 100), alignment=Alignment.END)
        children = [Component((0, 0), (80, 40)) for _ in range(4)]
        container.add_child(*children)

        self.assertEqual(children[0].rect.top, Container.SCROLL_PADDING)
        self.assertEqual(
            container._viewport_length(),
            100 - 2 * Container.SCROLL_PADDING,
        )

    def test_container_shadow_fades_out_from_panel_rgba(self):
        root = Component((0, 0), (100, 100))
        container = Container(
            cross_length=40,
            cross_percent=0,
            background_color=(200, 100, 50),
        )
        root.add_child(container)
        container.rect = pygame.Rect(30, 30, 40, 40)
        surface = pygame.Surface((100, 100), pygame.SRCALPHA)

        container.draw(surface)

        self.assertEqual(surface.get_at((30, 50)), pygame.Color(200, 100, 50, 204))
        self.assertLess(surface.get_at((30, 30)).a, surface.get_at((30, 50)).a)
        near_edge = surface.get_at((29, 50))
        farther_out = surface.get_at((20, 50))
        self.assertEqual(near_edge[:3], (200, 100, 50))
        self.assertGreater(near_edge.a, farther_out.a)
        self.assertEqual(surface.get_at((13, 50)).a, 0)

    def test_input_child_preserves_container_clip_for_later_siblings(self):
        root = Component((0, 0), (100, 100))
        container = Container(cross_length=100, cross_percent=0)
        root.add_child(container)
        container.rect = pygame.Rect(0, 20, 100, 100)
        painter = PaintedComponent((100, 30), (0, 255, 0))
        input_component = Input(
            (0, 0),
            100,
            pygame.font.Font(None, 16),
            placeholder_text="Input text",
        )
        container.add_child(painter, input_component)
        container.is_scrollable = True
        container.update_children_positions()
        container.is_scrollable = True
        surface = pygame.Surface((100, 140), pygame.SRCALPHA)

        container.draw(surface)

        self.assertEqual(surface.get_at((20, 10)).a, 0)
        self.assertEqual(surface.get_at((20, 50))[:3], (0, 255, 0))

    def test_scroll_wheel_event_is_consumed_before_nested_frame(self):
        from src.engine.ui.components.frame import Frame

        container = self.make_container((200, 200))
        simulation = SimpleNamespace(
            mouse_calls=[],
            simulation_speed=1.0,
            process_mouse=lambda *args, **kwargs: simulation.mouse_calls.append((args, kwargs)),
            advance=lambda _: None,
        )
        frame = Frame((0, 0), 80, simulation=simulation)
        content = Component((0, 0), (100, 160))
        container.add_child(frame, content)
        wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
        frame_data = make_frame_data(
            mouse_pos=(60, 60),
            events=[wheel_event],
            dt=1 / 60,
        )

        container.update(frame_data)

        self.assertTrue(frame_data.is_event_consumed(wheel_event))
        self.assertEqual(container.scroll_offset, 0)
        self.assertEqual(simulation.mouse_calls[0][0][2], 1)

    def test_frame_and_plot_fit_container_content_width(self):
        container = self.make_container((300, 120))
        frame = Frame((0, 0), 50)
        plot = Plot((0, 0), 150)
        container.add_child(frame, plot)

        container.update(make_frame_data(mouse_pos=(0, 0), events=[], dt=0))

        self.assertTrue(container.is_scrollable)
        expected_width = (
            300
            - 2 * container.cross_padding
            - container.SCROLLBAR_WIDTH
            - container.SCROLLBAR_GAP
        )
        self.assertEqual(frame.rect.width, expected_width)
        self.assertEqual(plot.rect.width, expected_width)
        self.assertEqual(plot.plot_surface.get_width(), expected_width)
        self.assertEqual(
            pygame.surfarray.array_alpha(plot.plot_surface).min(),
            255,
        )
        _, track = container._scrollbar_geometry(container.rect)
        self.assertEqual(frame.rect.right, track.left - container.SCROLLBAR_GAP)

        plot.set_live_data_source(
            lambda: ([0.0, 1.0], {"A": [1.0, 0.5], "B": [0.0, 0.5]}),
            title="Concentrations",
        )
        for _ in range(plot.LIVE_REFRESH_INTERVAL):
            plot._on_update(SimpleNamespace())

        self.assertEqual(
            [line.get_label() for line in plot.ax.lines],
            ["A", "B"],
        )
        self.assertEqual(list(plot.ax.lines[0].get_ydata()), [1.0, 0.5])

    def test_live_plot_only_rasterizes_when_data_revision_changes(self):
        revision = [0]
        value = [0.5]
        source_calls = [0]
        plot = Plot((0, 0), 100)

        def get_data():
            source_calls[0] += 1
            return [float(revision[0])], {"Value": [value[0]]}

        plot.set_live_data_source(
            get_data,
            title="Values",
            revision_source=lambda: revision[0],
        )
        redraw_calls = [0]
        plot.redraw = lambda: redraw_calls.__setitem__(0, redraw_calls[0] + 1)

        for _ in range(plot.LIVE_REFRESH_INTERVAL * 3):
            plot._on_update(SimpleNamespace())

        self.assertEqual(source_calls[0], 1)
        self.assertEqual(redraw_calls[0], 1)

        revision[0] += 1
        value[0] = 0.75
        for _ in range(plot.LIVE_REFRESH_INTERVAL):
            plot._on_update(SimpleNamespace())

        self.assertEqual(source_calls[0], 2)
        self.assertEqual(redraw_calls[0], 2)
        self.assertEqual(list(plot.ax.lines[0].get_ydata()), [0.75])

    def test_nested_container_scrolls_before_parent_and_bubbles_at_boundary(self):
        outer = self.make_container((200, 200))
        inner = Container(cross_length=200, cross_percent=0)
        inner_content = [Component((0, 0), (100, 50)) for _ in range(4)]
        inner.add_child(*inner_content)
        outer.add_child(inner, Component((0, 0), (100, 100)))
        event = pygame.event.Event(pygame.MOUSEWHEEL, y=-1)
        frame_data = make_frame_data(
            mouse_pos=(60, 80),
            events=[event],
        )

        outer.update(frame_data)

        self.assertTrue(frame_data.is_event_consumed(event))
        self.assertEqual(inner.scroll_offset, Container.SCROLL_STEP)
        self.assertEqual(outer.scroll_offset, 0)

        inner.scroll_offset = inner.content_length - inner._viewport_length()
        event_at_boundary = pygame.event.Event(pygame.MOUSEWHEEL, y=-1)
        frame_data = make_frame_data(
            mouse_pos=(60, 80),
            events=[event_at_boundary],
        )

        outer.update(frame_data)

        self.assertEqual(inner.scroll_offset, inner.content_length - inner._viewport_length())
        self.assertEqual(outer.scroll_offset, Container.SCROLL_STEP)
        self.assertEqual(
            inner_content[0].rect.top,
            inner.rect.top + Container.SCROLL_PADDING - inner.scroll_offset,
        )
        self.assertTrue(frame_data.is_event_consumed(event_at_boundary))


if __name__ == "__main__":
    unittest.main()
