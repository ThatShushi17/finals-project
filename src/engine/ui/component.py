import pygame
from ..frame_data import FrameData

from ...types import Dual
from ...enums import Position

class Component:
	def __init__(
		self,
		relative_position: Dual,
		size: Dual,
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		self.anchor = anchor
		self.dock = dock
		
		self.relative_position = relative_position
		self.size = size
		
		self.is_self_positioned = True
		self.children: list[Component] = []
		self.parent: Component
		self.margin_after: int
		self.rect = pygame.Rect((0, 0), size)

	def _on_update(self, frame_data: FrameData):
		pass

	def _on_adoption(self):
		pass

	def add_child(self, *children: "Component"):
		for child in children:
			self.children.append(child)
			child.parent = self
			child._on_adoption()

	def update(self, frame_data: FrameData):
		self._on_update(frame_data)

		self.handle_position(frame_data)
		
		for child in self.children:
			child.update(frame_data)

	def draw(self, surf: pygame.Surface):
		for child in self.children:
			child.draw(surf)

	def handle_position(self, frame_data: FrameData):
		if not self.is_self_positioned: return

		new_position = self.relative_position
		new_abs_x, new_abs_y = self._find_abs_position(new_position)
		new_abs_pos = (round(new_abs_x), round(new_abs_y))

		if new_abs_pos == self.rect.topleft: return

		self.rect.topleft = new_abs_pos

	def _find_abs_position(self, new_position: Dual):
		ax = self.anchor.value[0]
		ay = self.anchor.value[1]
		dx = self.dock.value[0]
		dy = self.dock.value[1]

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

		absx = new_position[0] + offx + self.parent.rect.left
		absy = new_position[1] + offy + self.parent.rect.top

		return (absx, absy)