import pygame
from .components import TabHandler
from .font_handler import FontHandler

class MenuSystem:
	def __init__(self, frame_data, window_size):
		self.frame_data = frame_data
		self.surf = pygame.Surface(window_size, pygame.SRCALPHA)
		self.font = FontHandler.load_font("Roboto-Regular.ttf", 16)
		self.tab_handler = TabHandler()

	def update(self):
		self.tab_handler.update(self.frame_data)

	def render(self):
		self.surf.fill((0, 0, 0, 0))

		self.tab_handler.draw(self.surf)

		return self.surf
