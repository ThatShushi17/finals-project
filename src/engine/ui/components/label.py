import pygame

from collections.abc import Callable

from ....types import Dual, Colorlike
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component

class Label(Component):
	def __init__(
		self,
		relative_position: Dual,
		font: pygame.font.Font,
		text_source: str | Callable[[], str],
		color: Colorlike | Callable[[], Colorlike] = (255, 255, 255),
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, (0, 0), anchor=anchor, dock=dock)

		self.text_source = text_source
		self.color = color
		self.font = font
		self._rendered_text: str | None = None
		self._rendered_color: pygame.Color | None = None
		
		self._create_surf()

	def _create_surf(self):
		text = self.text_source() if callable(self.text_source) else self.text_source
		color = pygame.Color(self.color() if callable(self.color) else self.color)
		if text == self._rendered_text and color == self._rendered_color:
			return

		self.text_surf = self.font.render(text, True, color)
		self._rendered_text = text
		self._rendered_color = color

		self.size = self.text_surf.get_size()
		self.rect.size = self.size

	def _on_update(self, frame_data: FrameData):
		self._create_surf()

	def draw(self, surf: pygame.Surface):
		dx, dy = self.offset
		self.rect.move_ip(dx, dy)

		surf.blit(self.text_surf, self.rect)

		self.rect.move_ip(-dx, -dy)

		super().draw(surf)