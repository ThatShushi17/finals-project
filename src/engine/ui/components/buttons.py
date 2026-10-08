import pygame

from ...frame_data import FrameData
from ..font_handler import FontHandler
from ..component import Component
from .labels import Label

from collections.abc import Callable

from ....types import Dual, Colorlike
from ....enums import Position

class Button(Component):
	border_radius = 12

	def __init__(
		self,
		relative_position: Dual,
		size: Dual,
		text_source: str | Callable[[], str],
		callback: Callable[[], None] = lambda: None,
		font: pygame.font.Font | None = None,
		color: Colorlike = (200, 200, 200),
		hover_color: Colorlike = (200, 255, 200),
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, size, anchor=anchor, dock=dock)
		
		self.color = color
		self.hover_color = hover_color
		self.callback = callback
		self.font = font if font is not None else FontHandler.default_font()
		
		self.is_hovered = False

		self.label = Label((0, 0), text_source, (0, 0, 0), self.font)
		self.add_child(self.label)
	
	def update(self, frame_data: FrameData):
		self.label.update(frame_data)
		
		self.handle_position(frame_data)
		self._on_update(frame_data)
	
	def _on_update(self, frame_data: FrameData):
		hover_status = self.rect.collidepoint(frame_data.mouse_pos)
		if hover_status != self.is_hovered:
			self.is_hovered = hover_status

		self.label.rect.center = self.rect.center

		self.check_clicked(frame_data.events)
	
	def draw(self, surf: pygame.Surface):
		color = self.hover_color if self.is_hovered else self.color

		pygame.draw.rect(surf, color, self.rect, border_radius=Button.border_radius)

		super().draw(surf)

	def check_clicked(self, events: list[pygame.event.Event]):
		for event in events:
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
				self.callback()
				return