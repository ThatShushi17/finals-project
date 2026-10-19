import pygame
import numpy as np
from collections.abc import Callable

from ...frame_data import FrameData
from ..component import Component

from ....enums import Axis, Alignment
from ....types import Colorlike

class Container(Component):
	SHADOW_DIFFUSION = 16
	BORDER_RADIUS = 12
	SCROLL_PADDING = 24
	CROSS_PADDING = 16
	SCROLLBAR_WIDTH = 8
	SCROLLBAR_GAP = 4
	SCROLLBAR_MARGIN = 4
	SCROLLBAR_MIN_HANDLE = 18
	SCROLL_STEP = 40

	def __init__(
		self,
		axis: Axis = Axis.VERTICAL,
		cross_length: int = 0,
		cross_percent: float = 0.8,
		alignment: Alignment = Alignment.CENTER,
		background_color: Colorlike | Callable[[], Colorlike] | None = None,
		cross_padding: int = CROSS_PADDING,
		scrollbar_handle_color: Colorlike | Callable[[], Colorlike] = (240, 240, 240),
		scrollbar_accent_color: Colorlike | Callable[[], Colorlike] = (106, 73, 255),
		scrollbar_track_color: Colorlike | Callable[[], Colorlike] = (180, 180, 180),
		fit_content: bool = False,
	):
		self.axis = axis
		self.alignment = alignment
		self.cross_length = cross_length
		self.cross_percent = cross_percent
		self.cross_padding = cross_padding
		self.fit_content = fit_content
		self.background_color = background_color
		self.scrollbar_handle_color = scrollbar_handle_color
		self.scrollbar_accent_color = scrollbar_accent_color
		self.scrollbar_track_color = scrollbar_track_color
		self.content_length = 0
		self.scroll_offset = 0
		self.is_scrollable = False
		self.is_scrollbar_dragging = False
		self.is_scrollbar_hovered = False
		self._scrollbar_drag_offset = 0
		self._background_cache_key = None
		self._background_shadow: pygame.Surface | None = None
		self._background_panel: pygame.Surface | None = None
		super().__init__((0, 0), (1, 1))

	def _on_adoption(self):
		self.update_rect()
		self.handle_position()
		self.update_children_positions()


	def update(self, frame_data: FrameData):
		self.update_rect()
		self.handle_position()
		for child in self.children:
			child._update_size()
		self._update_scroll_metrics()
		for child in self.children:
			child._update_size()
		self.update_children_positions()

		old_child_positions = [child.rect.topleft for child in self.children]
		for child in self.children:
			child.update(frame_data)

		self._handle_scroll_input(frame_data)
		self.update_children_positions()
		for child, old_position in zip(self.children, old_child_positions):
			delta_x = child.rect.left - old_position[0]
			delta_y = child.rect.top - old_position[1]
			if delta_x or delta_y:
				self._translate_descendants(child, delta_x, delta_y)

	def get_content_width(self) -> int:
		if self.axis == Axis.VERTICAL:
			width = self.rect.width - 2 * self.cross_padding
			if self.is_scrollable:
				width -= self.SCROLLBAR_WIDTH + self.SCROLLBAR_GAP
		else:
			width = (
				self.rect.width - 2 * self.SCROLL_PADDING
				if self.is_scrollable
				else self.rect.width
			)
		return max(0, width)

	@classmethod
	def _translate_descendants(cls, component: Component, dx: int, dy: int) -> None:
		for child in component.children:
			child.rect.move_ip(dx, dy)
			cls._translate_descendants(child, dx, dy)

	def _draw_background(self, surf: pygame.Surface) -> None:
		if self.background_color is None:
			return

		dx, dy = self.offset
		rect = self.rect.move(dx, dy)
		diffusion = self.SHADOW_DIFFUSION
		shadow = pygame.Surface(
			(rect.width + diffusion * 2, rect.height + diffusion * 2),
			pygame.SRCALPHA,
		)
		color = self.background_color() if callable(self.background_color) else self.background_color
		color = pygame.Color(color)
		panel_alpha = round(color.a * 0.8)
		cache_key = (
			rect.size,
			(color.r, color.g, color.b, color.a),
			diffusion,
			self.BORDER_RADIUS,
			panel_alpha,
		)

		if cache_key != self._background_cache_key:
			shadow = pygame.Surface(
				(rect.width + diffusion * 2, rect.height + diffusion * 2),
				pygame.SRCALPHA,
			)

			x, y = np.ogrid[
				-diffusion:rect.width + diffusion,
				-diffusion:rect.height + diffusion,
			]
			x = x + 0.5
			y = y + 0.5
			radius = min(self.BORDER_RADIUS, rect.width / 2, rect.height / 2)
			qx = np.abs(x - rect.width / 2) - (rect.width / 2 - radius)
			qy = np.abs(y - rect.height / 2) - (rect.height / 2 - radius)
			signed_distance = (
				np.hypot(np.maximum(qx, 0), np.maximum(qy, 0))
				+ np.minimum(np.maximum(qx, qy), 0)
				- radius
			)
			outside_distance = np.maximum(signed_distance, 0)
			fade = np.clip(outside_distance / diffusion, 0, 1)
			fade = fade * fade * (3 - 2 * fade)
			alpha = (panel_alpha * (1 - fade)).astype(np.uint8)
			alpha[signed_distance < 0] = 0

			pixels = pygame.surfarray.pixels3d(shadow)
			pixels[:, :, 0] = color.r
			pixels[:, :, 1] = color.g
			pixels[:, :, 2] = color.b
			del pixels
			pixels_alpha = pygame.surfarray.pixels_alpha(shadow)
			pixels_alpha[:, :] = alpha
			del pixels_alpha, alpha

			panel = pygame.Surface(rect.size, pygame.SRCALPHA)
			pygame.draw.rect(
				panel,
				(color.r, color.g, color.b, panel_alpha),
				panel.get_rect(),
				border_radius=self.BORDER_RADIUS,
			)
			self._background_cache_key = cache_key
			self._background_shadow = shadow
			self._background_panel = panel

		assert self._background_shadow is not None
		assert self._background_panel is not None
		surf.blit(
			self._background_shadow,
			(rect.left - diffusion, rect.top - diffusion),
		)
		surf.blit(self._background_panel, rect)

	def draw(self, surf: pygame.Surface):
		self._draw_background(surf)
		dx, dy = self.offset
		draw_rect = self.rect.move(dx, dy)
		clip_rect = draw_rect.copy()
		if self.axis == Axis.VERTICAL:
			clip_rect.left += self.cross_padding
			clip_rect.width = max(0, clip_rect.width - self.cross_padding * 2)
			if self.is_scrollable:
				clip_rect.width = max(
					0,
					clip_rect.width - self.SCROLLBAR_WIDTH - self.SCROLLBAR_GAP,
				)
				clip_rect.top += self.SCROLL_PADDING
				clip_rect.height = self._viewport_length()
		else:
			clip_rect.top += self.cross_padding
			clip_rect.height = max(0, clip_rect.height - self.cross_padding * 2)
			if self.is_scrollable:
				clip_rect.left += self.SCROLL_PADDING
				clip_rect.width = self._viewport_length()
				clip_rect.height = max(
					0,
					clip_rect.height - self.SCROLLBAR_WIDTH - self.SCROLLBAR_GAP,
				)

		previous_clip = surf.get_clip()
		surf.set_clip(previous_clip.clip(clip_rect))
		try:
			super().draw(surf)
		finally:
			surf.set_clip(previous_clip)

		ancestor = getattr(self, "parent", None)
		has_container_ancestor = False
		while ancestor is not None:
			if isinstance(ancestor, Container):
				has_container_ancestor = True
				break
			ancestor = getattr(ancestor, "parent", None)
		if not has_container_ancestor:
			self._draw_dropdown_popups(surf)

		if self.is_scrollable:
			self._draw_scrollbar(surf, draw_rect)

	def _draw_dropdown_popups(self, surf: pygame.Surface) -> None:
		from .dropdown import Dropdown

		def draw_popups(component: Component) -> None:
			if isinstance(component, Dropdown):
				component.draw_popup(surf)
			for child in component.children:
				draw_popups(child)

		for child in self.children:
			draw_popups(child)

	def _get_cross_axis_position(self, child: Component) -> int:
		if self.axis == Axis.VERTICAL:
			axis_index = 0
			parent_start = self.rect.left + self.cross_padding
			parent_length = self.get_content_width()
		else:
			axis_index = 1
			parent_start = self.rect.top + self.cross_padding
			parent_length = self.rect.height - self.cross_padding * 2

		anchor = child.anchor.value[axis_index]
		dock = child.dock.value[axis_index]
		child_length = child.rect.width if self.axis == Axis.VERTICAL else child.rect.height
		offset = parent_length / 2 if dock == "center" else parent_length if dock == "right" or dock == "bottom" else 0
		if anchor == "center":
			offset -= child_length / 2
		elif anchor == "right" or anchor == "bottom":
			offset -= child_length

		relative = child.relative_position[axis_index]
		return round(parent_start + relative + offset)

	def add_child(self, *children: Component):
		super().add_child(*children)
		for child in children:
			child.is_self_positioned = False
		if self.fit_content and hasattr(self, "parent"):
			self.update_rect()
		self.update_children_positions()

	def update_rect(self):
		parent_main_length = self.parent.rect.width if self.axis == Axis.HORIZONTAL else self.parent.rect.height
		parent_cross_length = self.parent.rect.width if self.axis == Axis.VERTICAL else self.parent.rect.height
		new_cross_length = self.cross_length or int(self.cross_percent * parent_cross_length)
		if self.fit_content:
			new_main_length = self._content_length() + 2 * self.SCROLL_PADDING
		else:
			new_main_length = parent_main_length

		new_size = (new_main_length, new_cross_length) if self.axis == Axis.HORIZONTAL else (new_cross_length, new_main_length)

		if new_size != self.rect.size:
			self.rect.size = new_size

	def update_children_positions(self):
		self._update_scroll_metrics()
		child_offsets: list[int] = []
		content_offset = 0

		for index, child in enumerate(self.children):
			child_offsets.append(content_offset)
			content_offset += child.rect.height if self.axis == Axis.VERTICAL else child.rect.width
			if index < len(self.children) - 1:
				content_offset += getattr(child, "margin_after", 0)

		container_length = (
			self.rect.height
			if self.axis == Axis.VERTICAL
			else self.rect.width
		)
		remaining_space = container_length - 2 * self.SCROLL_PADDING - self.content_length
		scroll_content = self.is_scrollable

		for index, child in enumerate(self.children):
			if scroll_content:
				alignment_offset = 0
			elif self.alignment == Alignment.CENTER:
				alignment_offset = round(remaining_space / 2)
			elif self.alignment == Alignment.END:
				alignment_offset = remaining_space
			elif self.alignment == Alignment.SPACE_BETWEEN and len(self.children) > 1:
				alignment_offset = round(remaining_space * index / (len(self.children) - 1))
			elif self.alignment == Alignment.SPACE_AROUND:
				alignment_offset = round(remaining_space * (index + 0.5) / len(self.children))
			else:
				alignment_offset = 0

			main_offset = self.SCROLL_PADDING + alignment_offset + child_offsets[index]
			if scroll_content:
				main_offset -= self.scroll_offset

			if self.axis == Axis.VERTICAL:
				new_abs_pos = (
					self._get_cross_axis_position(child),
					self.rect.top + main_offset,
				)
			else:
				new_abs_pos = (
					self.rect.left + main_offset,
					self._get_cross_axis_position(child),
				)

			if new_abs_pos != child.rect.topleft:
				child.rect.topleft = new_abs_pos

	def _main_length(self) -> int:
		return self.rect.height if self.axis == Axis.VERTICAL else self.rect.width

	def _content_length(self) -> int:
		return sum(
			(child.rect.height if self.axis == Axis.VERTICAL else child.rect.width)
			+ (getattr(child, "margin_after", 0) if index < len(self.children) - 1 else 0)
			for index, child in enumerate(self.children)
		)

	def _viewport_length(self) -> int:
		return max(1, self._main_length() - 2 * self.SCROLL_PADDING)

	def _update_scroll_metrics(self) -> None:
		self.content_length = self._content_length()
		self.is_scrollable = (
			self.content_length > 0
			and self.content_length > self._main_length() - 2 * self.SCROLL_PADDING
		)
		if not self.is_scrollable:
			self.scroll_offset = 0
		self.scroll_offset = min(
			max(0, self.scroll_offset),
			max(0, self.content_length - self._viewport_length()),
		)

	def _scrollbar_geometry(self, draw_rect: pygame.Rect) -> tuple[pygame.Rect, pygame.Rect]:
		track_length = self._viewport_length()
		track_length = max(1, track_length - self.SCROLLBAR_MARGIN * 2)
		max_scroll = max(1, self.content_length - self._viewport_length())
		handle_length = max(
			self.SCROLLBAR_MIN_HANDLE,
			round(track_length * self._viewport_length() / self.content_length),
		)
		handle_length = min(track_length, handle_length)
		scroll_range = max(0, track_length - handle_length)
		handle_offset = round(scroll_range * self.scroll_offset / max_scroll)

		if self.axis == Axis.VERTICAL:
			track = pygame.Rect(
				draw_rect.right - self.cross_padding - self.SCROLLBAR_WIDTH,
				draw_rect.top + self.SCROLL_PADDING + self.SCROLLBAR_MARGIN,
				self.SCROLLBAR_WIDTH,
				track_length,
			)
			handle = pygame.Rect(
				track.left,
				track.top + handle_offset,
				track.width,
				handle_length,
			)
		else:
			track = pygame.Rect(
				draw_rect.left + self.SCROLL_PADDING + self.SCROLLBAR_MARGIN,
				draw_rect.bottom - self.cross_padding - self.SCROLLBAR_WIDTH,
				track_length,
				self.SCROLLBAR_WIDTH,
			)
			handle = pygame.Rect(
				track.left + handle_offset,
				track.top,
				handle_length,
				track.height,
			)
		return track, handle

	def _main_axis_coordinate(self, point: tuple[int, int]) -> int:
		return point[1] if self.axis == Axis.VERTICAL else point[0]

	def _handle_scroll_input(self, frame_data: FrameData) -> None:
		if not self.is_scrollable:
			self.is_scrollbar_dragging = False
			return

		draw_rect = self.rect.move(*self.offset)
		track_rect, handle_rect = self._scrollbar_geometry(draw_rect)
		mouse_pos = frame_data.mouse_pos
		self.is_scrollbar_hovered = track_rect.collidepoint(mouse_pos)

		if self.is_scrollbar_dragging:
			mouse_coordinate = self._main_axis_coordinate(mouse_pos)
			handle_start = self._main_axis_coordinate(handle_rect.topleft)
			track_start = self._main_axis_coordinate(track_rect.topleft)
			scroll_range = max(
				1,
				(self._main_axis_coordinate(track_rect.bottomright) - track_start)
				- (self._main_axis_coordinate(handle_rect.bottomright) - handle_start),
			)
			track_range = max(1, self.content_length - self._viewport_length())
			self.scroll_offset = round(
				(mouse_coordinate - self._scrollbar_drag_offset - track_start)
				* track_range / scroll_range
			)
			self._update_scroll_metrics()

		for event in frame_data.events:
			if (
				frame_data.is_event_consumed(event)
				and not (
					self.is_scrollbar_dragging
					and event.type == pygame.MOUSEBUTTONUP
					and event.button == 1
				)
			):
				continue

			event_pos = getattr(event, "pos", mouse_pos)
			if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
				if self.is_scrollbar_dragging:
					self.is_scrollbar_dragging = False
					frame_data.consume_event(event)
			elif event.type == pygame.MOUSEMOTION and self.is_scrollbar_dragging:
				frame_data.consume_event(event)
			elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
				if not track_rect.collidepoint(event_pos):
					continue
				self.is_scrollbar_dragging = True
				self._scrollbar_drag_offset = (
					self._main_axis_coordinate(event_pos)
					- self._main_axis_coordinate(handle_rect.topleft)
				)
				if not handle_rect.collidepoint(event_pos):
					self._scrollbar_drag_offset = (
						self._main_axis_coordinate(handle_rect.size) // 2
					)
				frame_data.consume_event(event)
			elif self.rect.move(*self.offset).collidepoint(mouse_pos):
				if event.type == pygame.MOUSEWHEEL:
					target_offset = self.scroll_offset - event.y * self.SCROLL_STEP
					if self._scroll_to(target_offset):
						frame_data.consume_event(event)
				elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (4, 5):
					target_offset = self.scroll_offset + (-1 if event.button == 4 else 1) * self.SCROLL_STEP
					if self._scroll_to(target_offset):
						frame_data.consume_event(event)

		self._update_scroll_metrics()

	def _scroll_to(self, offset: int) -> bool:
		max_scroll = max(0, self.content_length - self._viewport_length())
		new_offset = min(max(0, offset), max_scroll)
		changed = new_offset != self.scroll_offset
		self.scroll_offset = new_offset
		return changed

	def _draw_scrollbar(self, surf: pygame.Surface, draw_rect: pygame.Rect) -> None:
		track_rect, handle_rect = self._scrollbar_geometry(draw_rect)
		track_color = self.scrollbar_track_color
		track_color = track_color() if callable(track_color) else track_color
		track_color = pygame.Color(track_color)
		track_color.a = round(255 * 0.6)

		track_surface = pygame.Surface(track_rect.size, pygame.SRCALPHA)
		track_surface.fill(track_color)
		surf.blit(track_surface, track_rect)

		handle_color = (
			self.scrollbar_accent_color
			if self.is_scrollbar_dragging or self.is_scrollbar_hovered
			else self.scrollbar_handle_color
		)
		handle_color = handle_color() if callable(handle_color) else handle_color
		pygame.draw.rect(surf, handle_color, handle_rect)