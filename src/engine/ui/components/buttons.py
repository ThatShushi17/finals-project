import pygame

from ...frame_data import FrameData
from ..component import Component
from .label import Label

from collections.abc import Callable

from ....types import Dual, Colorlike
from ....enums import Position


def _resolve_color(color: Colorlike | Callable[[], Colorlike]) -> Colorlike:
	return color() if callable(color) else color


class Button(Component):
	border_radius = 12
	PADDING_X = 16
	PADDING_Y = 8

	def __init__(
		self,
		relative_position: Dual,
		min_width: int,
		font: pygame.font.Font,
		text_source: str | Callable[[], str],
		callback: Callable[[], None] = lambda: None,
		color: Colorlike | Callable[[], Colorlike] = (200, 200, 200),
		background_color: Colorlike | Callable[[], Colorlike] = (20, 20, 20),
		hover_color: Colorlike | Callable[[], Colorlike] = (200, 255, 200),
		hover_text_color: Colorlike | Callable[[], Colorlike] = (255, 255, 255),
		border_color: Colorlike | Callable[[], Colorlike] = (0, 0, 0),
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		self.min_width = min_width
		self.font = font
		self.is_hovered = False
		self.label = Label(
			relative_position=(0, 0),
			text_source=text_source,
			font=font,
			color=lambda: _resolve_color(
				hover_text_color if self.is_hovered else color
			),
		)
		self.label._create_surf()
		label_width, label_height = self.label.text_surf.get_size()
		size = (
			max(min_width, label_width + 2 * self.PADDING_X),
			label_height + 2 * self.PADDING_Y,
		)
		super().__init__(relative_position, size, anchor=anchor, dock=dock)

		self.background_color = background_color
		self.hover_color = hover_color
		self.border_color = border_color
		self.hover_text_color = hover_text_color
		self.callback = callback
		self.add_child(self.label)

	def _update_size(self):
		self.label._create_surf()
		label_width, label_height = self.label.text_surf.get_size()
		self.size = (
			max(self.min_width, label_width + 2 * self.PADDING_X),
			label_height + 2 * self.PADDING_Y,
		)
		self.rect.size = self.size
	
	def _on_update(self, frame_data: FrameData):
		hover_status = self.rect.collidepoint(frame_data.mouse_pos)
		if hover_status != self.is_hovered:
			self.is_hovered = hover_status

		self.check_clicked(frame_data)
	
	def draw(self, surf: pygame.Surface):
		background_color = self.background_color
		background_color = background_color() if callable(background_color) else background_color
		border_color = self.hover_color if self.is_hovered else self.border_color
		border_color = border_color() if callable(border_color) else border_color

		dx, dy = self.offset
		self.rect.move_ip(dx, dy)

		pygame.draw.rect(surf, background_color, self.rect, border_radius=Button.border_radius)
		pygame.draw.rect(
			surf,
			border_color,
			self.rect,
			width=2,
			border_radius=Button.border_radius,
		)

		self.rect.move_ip(-dx, -dy)
		super().draw(surf)

	def check_clicked(self, frame_data: FrameData):
		for event in frame_data.events:
			if frame_data.is_event_consumed(event):
				continue
			if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.is_hovered:
				self.callback()
				frame_data.consume_event(event)
				return