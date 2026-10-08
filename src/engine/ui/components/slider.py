import pygame

from collections.abc import Callable

from ....types import Dual, Dualf
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component


class Slider(Component):
	def __init__(
		self,
		relative_position: Dual,
		width: int,
		initial_value: float | int,
		value_range: Dualf = (0.0, 1.0),
		on_change: Callable[[float | int], None] = lambda x: None,
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, (width, 20), anchor=anchor, dock=dock)
		self.value_range = value_range
		self.value = min(max(initial_value, value_range[0]), value_range[1])
		self.on_change = on_change

		self.is_dragging = False
		self.is_hovered = False

		self.track_color = (100, 100, 100)
		self.handle_color = (200, 200, 200)
		self.hover_color = (255, 255, 255)

	def _on_update(self, frame_data: FrameData):
		self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)

		for event in frame_data.events:
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if self.is_hovered:
					self.is_dragging = True
					self._update_value_from_mouse(frame_data.mouse_pos)
			elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				if self.is_dragging:
					self.is_dragging = False
			elif event.type == pygame.MOUSEMOTION:
				if self.is_dragging:
					self._update_value_from_mouse(frame_data.mouse_pos)

	def _update_value_from_mouse(self, mouse_pos: Dual):
		rel_x = mouse_pos[0] - self.rect.left
		ratio = rel_x / self.rect.width
		ratio = max(0.0, min(ratio, 1.0))
		
		new_value = self.value_range[0] + ratio * (self.value_range[1] - self.value_range[0])

		if isinstance(self.value_range[0], int) and isinstance(self.value_range[1], int):
			new_value = int(round(new_value))

		if new_value != self.value:
			self.value = new_value
			self.on_change(self.value)

	def draw(self, surf: pygame.Surface):
		# track
		track_rect = pygame.Rect(self.rect.left, self.rect.centery - 2, self.rect.width, 4)
		pygame.draw.rect(surf, self.track_color, track_rect)

		# handle
		ratio = 0 if self.value_range[1] == self.value_range[0] else (self.value - self.value_range[0]) / (self.value_range[1] - self.value_range[0])
		handle_x = self.rect.left + ratio * self.rect.width
		
		handle_rect = pygame.Rect(0, 0, 10, self.rect.height)
		handle_rect.center = (int(handle_x), self.rect.centery)
		
		color = self.hover_color if self.is_hovered or self.is_dragging else self.handle_color
		pygame.draw.rect(surf, color, handle_rect, border_radius=3)
		
		super().draw(surf)