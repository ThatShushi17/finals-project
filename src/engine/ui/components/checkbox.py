import pygame

from ...frame_data import FrameData
from ..component import Component

from collections.abc import Callable

from ....types import Dual
from ....enums import Position

class Checkbox(Component):
	def __init__(
		self,
		relative_position: Dual,
		size: Dual,
		initial_value: bool = False,
		on_change: Callable[[float | int], None] = lambda x: None,
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, size, anchor=anchor, dock=dock)
		self.value = initial_value
		self.on_change = on_change
		
		self.is_hovered = False
		
		self.bg_color = (30, 30, 30)
		self.border_color = (150, 150, 150)
		self.hover_color = (200, 200, 200)
		self.check_color = (100, 255, 100)
		
	def _on_update(self, frame_data: FrameData):
		self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)
		
		for event in frame_data.events:
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if self.is_hovered:
					self.value = not self.value
					self.on_change(self.value)

	def draw(self, surf: pygame.Surface):
		color = self.hover_color if self.is_hovered else self.border_color
		
		pygame.draw.rect(surf, self.bg_color, self.rect)
		pygame.draw.rect(surf, color, self.rect, width=2)
		
		if self.value:
			inner_rect = self.rect.inflate(-8, -8)
			pygame.draw.rect(surf, self.check_color, inner_rect)
			
		super().draw(surf)
