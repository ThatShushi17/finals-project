import pygame

from ...frame_data import FrameData
from ..component import Component

from collections.abc import Callable

from ....types import Colorlike, Dual
from ....enums import Position

class Checkbox(Component):
	def __init__(
		self,
		relative_position: Dual,
		size: Dual,
		initial_value: bool = False,
		on_change: Callable[[float | int], None] = lambda _: None,
		accent_color: Colorlike | Callable[[], Colorlike] = (100, 255, 100),
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, size, anchor=anchor, dock=dock)
		self.value = initial_value
		self.on_change = on_change
		
		self.is_hovered = False
		
		self.bg_color = (30, 30, 30)
		self.border_color = (80, 80, 80)
		self.accent_color = accent_color
		
	def _on_update(self, frame_data: FrameData):
		self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)

		for event in frame_data.events:
			if frame_data.is_event_consumed(event):
				continue
			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				if self.is_hovered:
					self.value = not self.value
					self.on_change(self.value)
					frame_data.consume_event(event)

	def draw(self, surf: pygame.Surface):
		color = self.accent_color if self.is_hovered or self.value else self.border_color
		color = color() if callable(color) else color

		dx, dy = self.offset
		self.rect.move_ip(dx, dy)
		
		pygame.draw.rect(surf, self.bg_color, self.rect)
		pygame.draw.rect(surf, color, self.rect, width=2)
		
		if self.value:
			inner_rect = self.rect.inflate(-8, -8)
			pygame.draw.rect(surf, color, inner_rect)

		self.rect.move_ip(-dx, -dy)

		super().draw(surf)
