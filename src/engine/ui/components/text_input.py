import pygame

from collections.abc import Callable

from ....types import Dual
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component
from ..font_handler import FontHandler

class TextInput(Component):
	def __init__(
		self,
		relative_position: Dual,
		size: Dual,
		initial_text: str = "",
		font: pygame.font.Font | None = None,
		on_change: Callable[[str], None] = lambda x: None,
		numeric_only: bool = False,
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, size, anchor=anchor, dock=dock)
		self.text = str(initial_text)
		self.on_change = on_change
		self.numeric_only = numeric_only
		self.font = font if font is not None else FontHandler.default_font()
		
		self.is_hovered = False
		self.is_active = False
		
		self.bg_color = (40, 40, 40)
		self.border_color = (100, 100, 100)
		self.active_color = (200, 200, 255)
		self.text_color = (255, 255, 255)
		
	def _on_update(self, frame_data: FrameData):
		self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)
		
		for event in frame_data.events:
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				self.is_active = self.is_hovered
			elif event.type == pygame.KEYDOWN:
				if self.is_active:
					if event.key == pygame.K_RETURN:
						self.is_active = False
						self.on_change(self.text)
					elif event.key == pygame.K_BACKSPACE:
						self.text = self.text[:-1]
						self.on_change(self.text)
					else:
						if self.numeric_only:
							if event.unicode.isdigit() or (event.unicode == '.' and '.' not in self.text) or (event.unicode == '-' and len(self.text) == 0):
								self.text += event.unicode
								self.on_change(self.text)
						else:
							self.text += event.unicode
							self.on_change(self.text)
								
	def draw(self, surf: pygame.Surface):
		border_color = self.active_color if self.is_active else (self.border_color if not self.is_hovered else (150, 150, 150))
		
		pygame.draw.rect(surf, self.bg_color, self.rect)
		pygame.draw.rect(surf, border_color, self.rect, width=2)
		
		text_surf = self.font.render(self.text, True, self.text_color)
		
		# Prevent rendering past the text box size
		surf.set_clip(self.rect)
		surf.blit(text_surf, (self.rect.left + 5, self.rect.centery - text_surf.get_height() // 2))
		surf.set_clip(None)
		
		super().draw(surf)
