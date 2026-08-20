import pygame

class Tab:
	def __init__(self, handler, children=None):
		self.handler = handler
		self.children = children if children is not None else []
		self.rect = pygame.Rect((0, 0), pygame.display.get_surface().get_size())

	def add_child(self, *children):
		for child in children:
			self.children.append(child)
			child.parent = self

	def update(self, frame_data):
		if frame_data.window_resized:
			self.rect.size = frame_data.window_size

		for child in self.children:
			child.update(frame_data)

	def draw(self, surf):
		for child in self.children:
			child.draw(surf)

class TabHandler:
	def __init__(self):
		self.stack = []

	def push(self, tab):
		self.stack.append(tab)

	def pop(self):
		if len(self.stack) > 1:
			self.stack.pop()

	def swap_to(self, tab):
		self.pop()
		self.push(tab)

	def update(self, frame_data):
		self.stack[-1].update(frame_data)

	def draw(self, surf):
		self.stack[-1].draw(surf)
