import pygame

from collections.abc import Callable

from ....types import Colorlike, Dual
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component

class Input(Component):
	PLACEHOLDER_OPACITY = 0.4
	PADDING_X = 5
	PADDING_Y = 6

	def __init__(
		self,
		relative_position: Dual,
		width: int,
		font: pygame.font.Font,
		placeholder_text: str = "",
		numeric_only: bool = False,
		on_change: Callable[[str], None] = lambda _: None,
		accent_color: Colorlike | Callable[[], Colorlike] = (106, 73, 255),
		border_color: Colorlike | Callable[[], Colorlike] = (100, 100, 100),
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		self.font = font
		self.placeholder_text = placeholder_text
		height = font.get_linesize() + 2 * self.PADDING_Y
		super().__init__(relative_position, (width, height), anchor=anchor, dock=dock)
		self.text = ""
		self.on_change = on_change
		self.numeric_only = numeric_only
		
		self.is_hovered = False
		self.is_active = False
		
		self.bg_color = (40, 40, 40)
		self.border_color = border_color
		self.accent_color = accent_color
		self.text_color = (255, 255, 255)
		self._cached_display_text: str | None = None
		self._cached_is_placeholder: bool | None = None
		self._cached_text_surface: pygame.Surface | None = None
		
	def _on_update(self, frame_data: FrameData):
		self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)
		
		for event in frame_data.events:
			if frame_data.is_event_consumed(event):
				continue
			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				self.is_active = self.is_hovered
				if self.is_hovered:
					frame_data.consume_event(event)
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
		display_text = self.text or self.placeholder_text
		is_placeholder = not self.text
		if (
			display_text != self._cached_display_text
			or is_placeholder != self._cached_is_placeholder
		):
			self._cached_text_surface = self.font.render(
				display_text,
				True,
				self.text_color,
			)
			if is_placeholder:
				self._cached_text_surface.set_alpha(
					int(255 * Input.PLACEHOLDER_OPACITY)
				)
			self._cached_display_text = display_text
			self._cached_is_placeholder = is_placeholder
		
		border_color = (
			self.accent_color
			if self.is_active
			else ((150, 150, 150) if self.is_hovered else self.border_color)
		)
		if callable(border_color):
			border_color = border_color()

		dx, dy = self.offset
		self.rect.move_ip(dx, dy)
		
		pygame.draw.rect(surf, self.bg_color, self.rect)
		pygame.draw.rect(surf, border_color, self.rect, width=2)
		
		assert self._cached_text_surface is not None
		text_surf = self._cached_text_surface

		previous_clip = surf.get_clip()
		surf.set_clip(previous_clip.clip(self.rect))
		try:
			surf.blit(text_surf, (self.rect.left + 5, self.rect.centery - text_surf.get_height() // 2))
		finally:
			surf.set_clip(previous_clip)
		
		self.rect.move_ip(-dx, -dy)

		super().draw(surf)
