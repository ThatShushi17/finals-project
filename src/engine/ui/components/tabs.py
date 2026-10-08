import pygame

from ...frame_data import FrameData
from ..component import Component

class Tab(Component):
	def __init__(self, handler: "TabHandler", children: list[Component] | None = None):
		super().__init__(
			relative_position = (0, 0),
			size = pygame.display.get_surface().get_size())

		self.handler = handler
		self.parent = self

		if children is not None:
			self.add_child(*children)


	def update(self, frame_data: FrameData):
		if frame_data.window_resized:
			self.rect.size = frame_data.window_size

		super().update(frame_data)


class TabHandler:
	def __init__(self):
		self.stack: list[Tab] = []

	def push(self, tab: Tab):
		self.stack.append(tab)

	def pop(self):
		if len(self.stack) > 1:
			self.stack.pop()

	def swap_to(self, tab: Tab):
		self.pop()
		self.push(tab)

	def update(self, frame_data: FrameData):
		self.stack[-1].update(frame_data)

	def draw(self, surf: pygame.Surface):
		self.stack[-1].draw(surf)


# TODO: Add an animation