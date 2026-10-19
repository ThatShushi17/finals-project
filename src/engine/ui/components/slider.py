import pygame

from collections.abc import Callable

from ....types import Colorlike, Dual
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component

# TODO: add color
class Slider(Component):
	def __init__(
		self,
		relative_position: Dual,
		width: int,
		initial_value: float | int,
		lower_bound: int | float = 0.0,
		upper_bound: int | float = 1.0,
		on_change: Callable[[float | int], None] = lambda _: None,
		accent_color: Colorlike | Callable[[], Colorlike] = (106, 73, 255),
		border_color: Colorlike | Callable[[], Colorlike] = (100, 100, 100),
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, (width, 20), anchor=anchor, dock=dock)
		self.lower_bound = lower_bound
		self.upper_bound = upper_bound
		self.value = min(max(initial_value, lower_bound), upper_bound)
		self.on_change = on_change

		self.is_dragging = False
		self.is_hovered = False

		self.track_color = (100, 100, 100)
		self.handle_color = (200, 200, 200)
		self.hover_color = (255, 255, 255)
		self.accent_color = accent_color
		self.border_color = border_color

	def _on_update(self, frame_data: FrameData):
		self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)

		for event in frame_data.events:
			owns_release = (
				self.is_dragging
				and event.type == pygame.MOUSEBUTTONUP
				and event.button == 1
			)
			if frame_data.is_event_consumed(event) and not owns_release:
				continue

			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if self.is_hovered:
					self.is_dragging = True
					self._update_value_from_mouse(frame_data.mouse_pos)
					frame_data.consume_event(event)
			elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				if self.is_dragging:
					self.is_dragging = False
					frame_data.consume_event(event)
			elif event.type == pygame.MOUSEMOTION:
				if self.is_dragging:
					self._update_value_from_mouse(frame_data.mouse_pos)
					frame_data.consume_event(event)

	def _update_value_from_mouse(self, mouse_pos: Dual):
		rel_x = mouse_pos[0] - self.rect.left
		ratio = rel_x / self.rect.width
		ratio = max(0.0, min(ratio, 1.0))
		
		new_value = self.lower_bound + ratio * (self.upper_bound - self.lower_bound)

		if isinstance(self.lower_bound, int) and isinstance(self.upper_bound, int):
			new_value = int(round(new_value))

		if new_value != self.value:
			self.value = new_value
			self.on_change(self.value)

	def draw(self, surf: pygame.Surface):
		dx, dy = self.offset
		self.rect.move_ip(dx, dy)

		# track
		track_rect = pygame.Rect(self.rect.left, self.rect.centery - 4, self.rect.width, 8)
		pygame.draw.rect(surf, self.track_color, track_rect)
		border_color = self.border_color
		border_color = border_color() if callable(border_color) else border_color
		pygame.draw.rect(surf, border_color, track_rect, width=1)

		# handle
		if self.upper_bound == self.lower_bound:
			ratio = 0
		else:
			ratio = (self.value - self.lower_bound) / (self.upper_bound - self.lower_bound)
		handle_x = self.rect.left + ratio * self.rect.width
		
		handle_rect = pygame.Rect(0, 0, 10, self.rect.height)
		handle_rect.center = (int(handle_x), self.rect.centery)
		
		color = self.accent_color if self.is_hovered or self.is_dragging else self.handle_color
		color = color() if callable(color) else color
		pygame.draw.rect(surf, color, handle_rect, border_radius=3)
		
		self.rect.move_ip(-dx, -dy)

		super().draw(surf)