from __future__ import annotations

import pygame
from typing import TYPE_CHECKING

from ...frame_data import FrameData
from ..component import Component

from ....types import Dual, Colorlike
from ....enums import Position

from collections.abc import Callable

if TYPE_CHECKING:
    from ...simulation.simulation import Simulation


class Frame(Component):
    def __init__(
        self,
        relative_position: Dual,
        height: int,
        simulation: Simulation | None = None,
        background_color: Colorlike = (39, 39, 39),
        accent_color: Colorlike | Callable[[], Colorlike] | None = (106, 73, 255),
        anchor: Position = Position.CENTER,
        dock: Position = Position.CENTER
    ):
        super().__init__(relative_position, (1, height), anchor=anchor, dock=dock)
        self.height = height
        self.simulation = simulation
        self.background_color = background_color
        self.border_color = accent_color
        self.border_width = 2
        
        # Internal state ported from deprecated Viewport
        self.is_hovered = False
        self.is_dragging = False
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_scroll = 0

    def _on_adoption(self):
        self._update_size()

    def _update_size(self):
        if not hasattr(self, "parent"):
            return

        width = self.parent.get_content_width()
        self.size = (width, self.height)
        self.rect.size = self.size

    def _on_update(self, frame_data: FrameData):
        draw_rect = self.rect.move(*self.offset)
        self.is_hovered = draw_rect.collidepoint(frame_data.mouse_pos)
        
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_scroll = 0
        
        for event in frame_data.events:
            owns_release = (
                self.is_dragging
                and event.type == pygame.MOUSEBUTTONUP
                and event.button == 1
            )
            if frame_data.is_event_consumed(event) and not owns_release:
                continue

            if event.type == pygame.MOUSEBUTTONDOWN:
                event_pos = getattr(event, "pos", frame_data.mouse_pos)
                if draw_rect.collidepoint(event_pos) and self.simulation is not None:
                    if event.button == 1:
                        self.is_dragging = True
                        frame_data.consume_event(event)
                    elif event.button == 4:
                        self.mouse_scroll = 1
                        frame_data.consume_event(event)
                    elif event.button == 5:
                        self.mouse_scroll = -1
                        frame_data.consume_event(event)
            elif (
                event.type == pygame.MOUSEWHEEL
                and self.is_hovered
                and self.simulation is not None
            ):
                self.mouse_scroll += event.y
                frame_data.consume_event(event)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.is_dragging:
                        frame_data.consume_event(event)
                    self.is_dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.is_dragging:
                    self.mouse_dx, self.mouse_dy = event.rel
                    frame_data.consume_event(event)

        if self.simulation is not None:
            if (
                self.mouse_dx != 0
                or self.mouse_dy != 0
                or self.mouse_scroll != 0
            ):
                self.simulation.process_mouse(
                    self.mouse_dx,
                    self.mouse_dy,
                    self.mouse_scroll,
                    panning=self.is_dragging,
                    mouse_pos=(
                        frame_data.mouse_pos[0] - draw_rect.left,
                        frame_data.mouse_pos[1] - draw_rect.top,
                    ),
                    frame_rect=pygame.Rect((0, 0), self.rect.size),
                )
                
            self.simulation.advance(
                frame_data.dt * self.simulation.simulation_speed
            )

    def draw(self, surf: pygame.Surface):
        dx, dy = self.offset
        draw_rect = self.rect.move(dx, dy)
        clipped_rect = draw_rect.clip(surf.get_clip())
        if clipped_rect.width <= 0 or clipped_rect.height <= 0:
            return

        frame_surf = surf.subsurface(clipped_rect)
        frame_surf.fill(self.background_color)

        if self.simulation is not None:
            self.simulation.render(frame_surf, frame_rect=frame_surf.get_rect())

        if self.border_color is not None:
            border_color = self.border_color
            if callable(border_color):
                border_color = border_color()
            pygame.draw.rect(
                surf,
                border_color,
                draw_rect,
                self.border_width,
            )

        super().draw(surf)