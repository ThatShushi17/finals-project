from enum import Enum

from ...frame_data import FrameData
from ..component import Component


class Axis(Enum):
	"""Enum for container layout axis direction."""
	VERTICAL = "vertical"
	HORIZONTAL = "horizontal"


class Alignment(Enum):
	"""Enum for content alignment along the main axis."""
	START = "start"
	CENTER = "center"
	END = "end"
	SPACE_BETWEEN = "space_between"
	SPACE_AROUND = "space_around"


class Container(Component):
	def __init__(
		self,
		axis: Axis = Axis.VERTICAL,
		cross_length: int = 200,
		cross_percent: float = 0.8,
		alignment: Alignment = Alignment.CENTER
	):
		self.axis = axis
		self.alignment = alignment
		self.cross_length = cross_length
		self.cross_percent = cross_percent
		super().__init__((0, 0), (1, 1))

	def _on_adoption(self):
		width = self.cross_length if self.axis == Axis.VERTICAL else self.parent.rect.width
		height = self.cross_length if self.axis == Axis.HORIZONTAL else self.parent.rect.height
		
		self.rect.size = (width, height)

	def update(self, frame_data: FrameData):
		self.update_rect(frame_data)
		self.handle_position(frame_data)
		self.update_children_positions(frame_data)

		for child in self.children:
			child.update(frame_data)

	def add_child(self, *children: Component):
		super().add_child(*children)
		for child in children:
			child.is_self_positioned = False

	def define_margins(self, *margins: int):
		if len(margins) != len(self.children):
			raise ValueError(f"Container {self} has {len(self.children)} children but tried to define {len(margins)} margins")
	
		for child, margin in zip(self.children, margins):
			child.margin_after = margin

	def update_rect(self, frame_data: FrameData):
		new_main_length = self.parent.rect.width if self.axis == Axis.HORIZONTAL else self.parent.rect.height
		new_cross_length = 0
		if self.cross_length:
			new_cross_length = self.cross_length
		elif self.cross_percent:
			new_cross_length = self.cross_percent * (frame_data.window_size[0] if self.axis == Axis.VERTICAL else frame_data.window_size[1])

		new_size = (new_main_length, int(new_cross_length)) if self.axis == Axis.HORIZONTAL else (int(new_cross_length), new_main_length)

		if new_size != self.rect.size:
			self.rect.size = new_size

	def update_children_positions(self, frame_data: FrameData):
		current_offset = 0
		child_offsets: list[int] = []

		for child in self.children:
			child_offsets.append(current_offset)
			current_offset += child.margin_after + (child.rect.height if self.axis == Axis.VERTICAL else child.rect.width)

		# Calculate centering offset based on alignment
		# centerising_offset = current_offset / 2 if self.alignment == Alignment.CENTER else 0

		container_length = (
			self.rect.height
			if self.axis == Axis.VERTICAL
			else self.rect.width
		)

		centerising_offset = int(
			(container_length - current_offset) / 2
			if self.alignment == Alignment.CENTER
			else 0
		)

		for i in range(len(self.children)):
			child = self.children[i]

			if self.axis == Axis.VERTICAL:
				new_position = (
					child.relative_position[0],
					child_offsets[i] - centerising_offset
				)
			else:
				new_position = (
					child_offsets[i] - centerising_offset,
					child.relative_position[1]
				)

			new_abs_x, new_abs_y = child._find_abs_position(new_position)
			new_abs_pos = (round(new_abs_x), round(new_abs_y))

			if new_abs_pos != child.rect.topleft:
				child.rect.topleft = new_abs_pos