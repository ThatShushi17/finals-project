import pygame
from enum import Enum


class Position(Enum):
	"""Enum for 9-point positioning grid (anchor/dock)."""
	TOP_LEFT = ("left", "top")
	TOP_CENTER = ("center", "top")
	TOP_RIGHT = ("right", "top")
	CENTER_LEFT = ("left", "center")
	CENTER = ("center", "center")
	CENTER_RIGHT = ("right", "center")
	BOTTOM_LEFT = ("left", "bottom")
	BOTTOM_CENTER = ("center", "bottom")
	BOTTOM_RIGHT = ("right", "bottom")


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

class Component:
	def __init__(self, rel_pos, size, anchor=None, dock=None):
		if anchor is None:
			anchor = Position.CENTER
		if dock is None:
			dock = Position.CENTER
		
		if isinstance(anchor, Position):
			self.anchor = anchor.value
		else:
			self.anchor = anchor
		
		if isinstance(dock, Position):
			self.dock = dock.value
		else:
			self.dock = dock
		
		self.rel_pos = rel_pos
		self.size = size
		
		self.is_self_positioned = True
		self.parent = None
		self.children = []
		self.position_callback = lambda comp, frame_data: comp.rel_pos
		self.rect = pygame.Rect((0, 0), size)

	def _on_update(self, frame_data):
		pass

	def _on_adoption(self):
		pass

	def add_child(self, *children):
		for child in children:
			self.children.append(child)
			child.parent = self
			child._on_adoption()

	def update(self, frame_data):
		self.handle_position(frame_data)

		self._on_update(frame_data)

		for child in self.children:
			child.update(frame_data)

	def draw(self, surf):
		for child in self.children:
			child.draw(surf)

	def handle_position(self, frame_data):
		if not self.is_self_positioned: return

		new_pos = self.position_callback(self, frame_data)
		new_abs_x, new_abs_y = self._find_abs_position(new_pos)
		new_abs_pos = (round(new_abs_x), round(new_abs_y))

		if new_abs_pos == self.rect.topleft: return

		self.rect.topleft = new_abs_pos

	def _find_abs_position(self, new_pos):
		ax = self.anchor[0]
		ay = self.anchor[1]
		dx = self.dock[0]
		dy = self.dock[1]

		offx = 0
		offy = 0
		
		if dx == "center":
			offx = self.parent.rect.width / 2
		elif dx == "right":
			offx = self.parent.rect.width

		if dy == "center":
			offy = self.parent.rect.height / 2
		elif dy == "bottom":
			offy = self.parent.rect.height

		if ax == "center":
			offx -= self.rect.width / 2
		elif ax == "right":
			offx -= self.rect.width

		if ay == "center":
			offy -= self.rect.height / 2
		elif ay == "bottom":
			offy -= self.rect.height

		absx = new_pos[0] + offx + self.parent.rect.left
		absy = new_pos[1] + offy + self.parent.rect.top

		return (absx, absy)