# import pygame
from ..core import Component

class Label(Component):
	def __init__(self, rel_pos, text_source, color, font, anchor=None, dock=None):
		super().__init__(rel_pos, (0, 0) ,anchor=anchor, dock=dock)

		self.text_source = text_source
		self.color = color
		self.font = font

		self.is_dynamic = callable(self.text_source)
		self.text_surf = None
		
		# Always start with empty string; update_text() will populate for dynamic
		self.cur_text = ""
		self.needs_create_surf = True

	def _create_surf(self):
		# Get text: use cur_text for dynamic, text_source for static
		text = self.cur_text if self.is_dynamic else self.text_source
		# Ensure text is a string before rendering
		text = str(text) if text is not None else ""
		self.text_surf = self.font.render(text, True, self.color)

		self.size = self.text_surf.get_size()
		self.rect.size = self.size

	def _on_update(self, frame_data):
		# For static text, create surface on first update
		if self.needs_create_surf and not self.is_dynamic:
			self._create_surf()
			self.needs_create_surf = False
		
		self.update_text(frame_data)

	def update_text(self, frame_data):
		if not self.is_dynamic: return

		new_text = str(self.text_source())
		if new_text != self.cur_text:
			self.cur_text = new_text
			self._create_surf()

	def draw(self, surf):
		if not self.text_surf:
			self._create_surf()

		surf.blit(self.text_surf, self.rect)

		super().draw(surf)