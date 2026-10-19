import pygame
import numpy as np
from collections.abc import Callable
from ..images import ARTEMIS_IMAGE, HEX_IMAGE, load_cover_image

from ....types import Dual, Colorlike
from ....enums import Cardinal, HexFadeCorner, TabBackgrounds
from ...frame_data import FrameData
from ..component import Component


def _prepare_hex_image(
	image: pygame.Surface,
	accent: pygame.Color,
	fade_corner: HexFadeCorner,
) -> pygame.Surface:
	pixels = pygame.surfarray.pixels3d(image)
	alpha = pygame.surfarray.pixels_alpha(image)

	intensity = pixels[:, :, 0].copy()
	source_alpha = alpha.copy()

	# Store the tint in BGR order before the channel swap used by the UI image path.
	intensity = intensity.astype(np.uint16)
	pixels[:, :, 0] = intensity * accent.b // 255
	pixels[:, :, 1] = intensity * accent.g // 255
	pixels[:, :, 2] = intensity * accent.r // 255
	pixels[:, :, [0, 2]] = pixels[:, :, [2, 0]].copy()

	width, height = image.get_size()
	origin_x = width - 1 if fade_corner in (HexFadeCorner.TOP_RIGHT, HexFadeCorner.BOTTOM_RIGHT) else 0
	origin_y = height - 1 if fade_corner in (HexFadeCorner.BOTTOM_LEFT, HexFadeCorner.BOTTOM_RIGHT) else 0

	x, y = np.ogrid[:width, :height]
	distance = np.hypot(x - origin_x, y - origin_y)
	visible_radius = max(1.0, min(width, height) * 0.55)
	fade_width = max(1.0, min(width, height) * 0.35)
	fade_progress = np.clip((distance - visible_radius) / fade_width, 0.0, 1.0)
	fade_progress = fade_progress * fade_progress * (3.0 - 2.0 * fade_progress)
	alpha[:, :] = (source_alpha * (1.0 - fade_progress)).astype(np.uint8)

	del pixels, alpha
	return image


class Tab(Component):
	def __init__(self,
		handler: "TabHandler",
		background_color:  Colorlike | Callable[[], Colorlike],
		home: Cardinal = Cardinal.BOTTOM,
		background: tuple[TabBackgrounds, Colorlike | Callable[[], Colorlike]] = (TabBackgrounds.SOLID, "#6A49FF"),
		children: list[Component] | None = None,
		hex_fade_corner: HexFadeCorner = HexFadeCorner.BOTTOM_LEFT,
	):
		super().__init__(
			relative_position = (0, 0),
			size = handler.frame_data.window_size
		)

		self.handler = handler
		self.parent = handler.root
		self.home = home
		self.hex_fade_corner = hex_fade_corner

		self.background_color = background_color
		self.background = background

		if children is not None:
			self.add_child(*children)

	@property
	def home_coord(self):
		match self.home:
			case Cardinal.TOP:
				return (
					0,
					-self.handler.frame_data.window_size[1]
				)

			case Cardinal.BOTTOM:
				return (
					0,
					self.handler.frame_data.window_size[1]
				)

			case Cardinal.LEFT:
				return (
					-self.handler.frame_data.window_size[0],
					0
				)

			case Cardinal.RIGHT:
				return (
					self.handler.frame_data.window_size[0],
					0
				)

	def update(self, frame_data: FrameData):
		if frame_data.window_resized:
			self.rect.size = frame_data.window_size

		super().update(frame_data)

	def _get_background_color(self) -> pygame.Color:
		return pygame.Color(self.background_color() if callable(self.background_color) else self.background_color)


	def _get_accent_color(self) -> pygame.Color:
		color = self.background[1]
		return pygame.Color(color() if callable(color) else color)


	def _draw_main_background(self, surf: pygame.Surface) -> None:
		rect = self.rect
		color = self._get_background_color()

		pygame.draw.rect(surf, color, rect)

		if not ARTEMIS_IMAGE.is_file():
			return

		# Cache the scaled image for this window size.
		cache_key = (rect.width, rect.height)
		if not hasattr(self, "_main_image_cache"):
			self._main_image_cache: dict[tuple[int, int], pygame.Surface] = {}

		if cache_key not in self._main_image_cache:
			image = load_cover_image(
				ARTEMIS_IMAGE, (rect.width, rect.height)
			)

			# Mandatory RGB -> BGR channel swap.
			pixels = pygame.surfarray.pixels3d(image)
			pixels[:, :, [0, 2]] = pixels[:, :, [2, 0]].copy()
			del pixels

			self._main_image_cache[cache_key] = image

		image = self._main_image_cache[cache_key]

		# Draw the original image without modifying its brightness.
		surf.blit(image, rect.topleft)

		fade_length = min(rect.height // 3, 80)
		solid_length = min(rect.height // 5, 140)

		# The entire affected region is fade_length + solid_length.
		fade_start = rect.height - fade_length - solid_length

		if fade_length > 0:
			color_key = (color.r, color.g, color.b, color.a)
			cache_key = (rect.width, fade_length, color_key)
			if not hasattr(self, "_main_fade_cache"):
				self._main_fade_cache: dict[
					tuple[int, int, tuple[int, int, int, int]],
					pygame.Surface,
				] = {}

			if cache_key not in self._main_fade_cache:
				fade = pygame.Surface(
					(rect.width, fade_length),
					pygame.SRCALPHA,
				)
				for y in range(fade_length):
					t = y / max(fade_length - 1, 1)
					alpha = round(255 * (1 - (1 - t) ** 2))
					pygame.draw.line(
						fade,
						(color.r, color.g, color.b, alpha),
						(0, y),
						(rect.width - 1, y),
					)
				self._main_fade_cache[cache_key] = fade

			surf.blit(
				self._main_fade_cache[cache_key],
				(rect.left, rect.top + fade_start),
			)

		# The remaining solid_length pixels are pure background_color.
		pygame.draw.rect(
			surf,
			color,
			(
				rect.left,
				rect.top + fade_start + fade_length,
				rect.width,
				solid_length,
			),
		)


	def _draw_hex_background(self, surf: pygame.Surface) -> None:
		rect = self.rect
		color = self._get_background_color()

		pygame.draw.rect(surf, color, rect)

		if not HEX_IMAGE.is_file():
			return

		accent = self._get_accent_color()
		cache_key = (rect.width, rect.height, accent.r, accent.g, accent.b)
		if not hasattr(self, "_hex_image_cache"):
			self._hex_image_cache: dict[tuple[int, int, int, int, int], pygame.Surface] = {}

		if cache_key not in self._hex_image_cache:
			image = load_cover_image(
				HEX_IMAGE, (rect.width, rect.height)
			)
			self._hex_image_cache[cache_key] = _prepare_hex_image(image, accent, self.hex_fade_corner)

		# Draw the original image without modifying its brightness.
		surf.blit(self._hex_image_cache[cache_key], rect.topleft)


	def draw(self, surf: pygame.Surface):
		kind, _ = self.background

		dx, dy = self.offset
		self.rect.move_ip(dx, dy)
		try:
			if kind == TabBackgrounds.MAIN:
				self._draw_main_background(surf)
			elif kind == TabBackgrounds.HEX:
				self._draw_hex_background(surf)
			else:
				pygame.draw.rect(surf, self._get_background_color(), self.rect)
		finally:
			self.rect.move_ip(-dx, -dy)

		super().draw(surf)


class TabHandler:
	TRANSITION_DURATION_MS = 600

	def __init__(self, root: Component, frame_data: FrameData):
		self.root = root
		self.frame_data = frame_data

		# self.stack: list[Tab] = []
		# self.docked: list[Tab] = []
		# self.inbound: list[Tab] = []
		# self.outbound: list[Tab] = []
		# self.active: Tab

		self._active: list[Tab] = []
		self._history: list[Tab] = []
		self._transitions: dict[Tab, tuple[Dual, Dual, int]] = {}
		self._transition_destination: Tab | None = None

	def push(self, tab: Tab):
		self._active.clear()
		self._history.clear()
		self._transitions.clear()
		self._transition_destination = None
		tab.set_offset((0, 0))
		self._active.append(tab)

	def push_immediate(self, tab: Tab):
		if self._active:
			current = self._active[-1]
			if current is tab:
				return
			self._history.append(current)

		self._transitions.clear()
		self._transition_destination = None
		tab.set_offset((0, 0))
		self._active = [tab]

	def pop_immediate(self):
		if not self._active or not self._history:
			return

		current = self._active[-1]
		current.set_offset((0, 0))
		previous = self._history.pop()
		previous.set_offset((0, 0))
		self._transitions.clear()
		self._transition_destination = None
		self._active = [previous]

	def open(self, tab: Tab):
		if self._transitions:
			return

		self._active.append(tab)
		start_offset = tab.home_coord
		self._start_transition(
			{tab: (start_offset, (0, 0))},
			tab,
		)

	def close_to(self, tab: Tab):
		if self._transitions or not self._active:
			return

		current = self._active[-1]
		if current is tab:
			return

		if tab in self._history:
			self._history = self._history[:self._history.index(tab)]

		height = self.frame_data.window_size[1]
		self._active = [tab, current]
		self._start_transition(
			{
				tab: ((0, -height), (0, 0)),
				current: ((0, 0), (0, height)),
			},
			tab,
		)

	def shove(self, tab: Tab):
		if self._transitions:
			return
		if not self._active:
			self.push(tab)
			return

		current = self._active[-1]
		if current is tab:
			return

		height = self.frame_data.window_size[1]
		self._history.append(current)
		self._active = [current, tab]
		self._start_transition(
			{
				current: ((0, 0), (0, -height)),
				tab: ((0, height), (0, 0)),
			},
			tab,
		)

	def reverse_shove(self):
		if self._transitions or not self._history or not self._active:
			return

		current = self._active[-1]
		previous = self._history.pop()
		if previous is current:
			return

		height = self.frame_data.window_size[1]
		self._active = [previous, current]
		self._start_transition(
			{
				previous: ((0, -height), (0, 0)),
				current: ((0, 0), (0, height)),
			},
			previous,
		)

	def _start_transition(
		self,
		transitions: dict[Tab, tuple[Dual, Dual]],
		destination: Tab,
	):
		start_time = pygame.time.get_ticks()
		self._transitions = {
			tab: (start, end, start_time)
			for tab, (start, end) in transitions.items()
		}
		for tab, (start, _, _) in self._transitions.items():
			tab.set_offset(start)
		self._transition_destination = destination

	def update(self, frame_data: FrameData):
		if not self._active:
			return

		if self._transitions:
			tab = next(iter(self._transitions))
			_, _, start_time = self._transitions[tab]
			progress = min(
				(pygame.time.get_ticks() - start_time) / self.TRANSITION_DURATION_MS,
				1.0,
			)
			eased_progress = progress * progress * (3 - 2 * progress)

			for moving_tab, (start_offset, end_offset, _) in self._transitions.items():
				moving_tab.set_offset((
					round(start_offset[0] + (end_offset[0] - start_offset[0]) * eased_progress),
					round(start_offset[1] + (end_offset[1] - start_offset[1]) * eased_progress),
				))

			if progress >= 1 and self._transition_destination is not None:
				destination = self._transition_destination
				destination.set_offset((0, 0))
				self._transitions.clear()
				self._transition_destination = None
				self._active = [destination]

		self._active[-1].update(frame_data)

	def is_active(self, tab: Tab) -> bool:
		return tab in self._active

	def draw(self, surf: pygame.Surface, offset: Dual = (0, 0)):
		for tab in self._active:
			tab.draw(surf)
