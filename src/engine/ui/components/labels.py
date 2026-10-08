import pygame

from collections.abc import Callable

from ....types import Dual, Colorlike
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component
from ..font_handler import FontHandler

class Label(Component):
	def __init__(
		self,
		relative_position: Dual,
		text_source: str | Callable[[], str],
		color: Colorlike = (255, 255, 255),
		font: pygame.font.Font | None = None,
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, (0, 0) ,anchor=anchor, dock=dock)

		self.text_source = text_source
		self.color = color
		self.font = font if font is not None else FontHandler.default_font()
		
		self.cur_text = ""
		self.needs_create_surf = True

		self.text_surf: pygame.Surface
		self._create_surf()

	def _create_surf(self):
		text = self.cur_text if callable(self.text_source) else self.text_source
		text = text if text else ""
		self.text_surf = self.font.render(text, True, self.color)

		self.size = self.text_surf.get_size()
		self.rect.size = self.size

	def _on_update(self, frame_data: FrameData):
		if self.needs_create_surf and not callable(self.text_source):
			self._create_surf()
			self.needs_create_surf = False
		
		self.update_text()

	def update_text(self):
		if not callable(self.text_source): return

		new_text = self.text_source()
		if new_text != self.cur_text:
			self.cur_text = new_text
			self._create_surf()

	def draw(self, surf: pygame.Surface):
		if not self.text_surf:
			self._create_surf()

		surf.blit(self.text_surf, self.rect)

		super().draw(surf)