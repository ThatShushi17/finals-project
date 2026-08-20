import pygame
from ..core import Component
from .labels import Label
from ..font_handler import FontHandler

class Button(Component):
	border_rad = 5

	def __init__(self, rel_pos, size, text_source, callback, font=None, color=(200, 200, 200), hover_color=(200, 255, 200), anchor=None, dock=None):
		super().__init__(rel_pos, size, anchor=anchor, dock=dock)
		
		self.text_source = text_source
		self.color = color
		self.hover_color = hover_color
		self.callback = callback
		self.font = font if font is not None else FontHandler.load_font("Roboto-Regular.ttf", 16)
		
		self.is_hovered = False

		self.label = Label((0, 0), text_source, (0, 0, 0), self.font)
		self.add_child(self.label)
	
	def update(self, frame_data):
		# Update label first so it has correct size before we center it
		self.label.update(frame_data)
		
		# Then handle position and call _on_update (which centers the label)
		self.handle_position(frame_data)
		self._on_update(frame_data)
		
		# Don't call super().update() to avoid updating label twice
	
	def _on_update(self, frame_data):
		hover_status = self.rect.collidepoint(frame_data.mouse_pos)
		if hover_status != self.is_hovered:
			self.is_hovered = hover_status

		# Position label at center of button
		self.label.rect.center = self.rect.center

		self.check_clicked(frame_data.events)
	
	def draw(self, surf):
		color = self.hover_color if self.is_hovered else self.color

		pygame.draw.rect(surf, color, self.rect, border_radius=Button.border_rad)

		super().draw(surf)

	def check_clicked(self, events):
		for event in events:
			if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.is_hovered:
				self.callback()
				return