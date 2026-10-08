import pygame

class FrameData:
	def __init__(self):
		self.cur_frame = -1
		self.window_size = pygame.display.get_surface().get_size()

	def update(self):
		self.cur_frame += 1

		self.mouse_pos = pygame.mouse.get_pos()
		self.events = pygame.event.get()
		self.dt = pygame

		new_window_size = pygame.display.get_surface().get_size()
		self.window_resized = new_window_size == self.window_size
		self.window_size = new_window_size
