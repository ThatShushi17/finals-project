import pygame
import matplotlib
from collections.abc import Callable, Sequence

matplotlib.use("Agg") 
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from ...frame_data import FrameData
from ....types import Dual
from ....enums import Position

from ..component import Component

class Plot(Component):
	def __init__(
		self,
		relative_position: Dual,
		height: int,
		dpi: int = 100,
		anchor: Position = Position.CENTER,
		dock: Position = Position.CENTER
	):
		super().__init__(relative_position, (1, height), anchor, dock)
		self.height = height
		self.dpi = dpi

		fig_width = self.size[0] / self.dpi
		fig_height = self.height / self.dpi

		self.fig = Figure(figsize=(fig_width, fig_height), dpi=self.dpi)
		self.canvas = FigureCanvas(self.fig)
		self.ax = self.fig.add_subplot(111)
		self.plot_surface = None
		self.data_source: Callable[
			[],
			tuple[Sequence[float], dict[str, Sequence[float]]],
		] | None = None
		self.revision_source: Callable[[], int] | None = None
		self.live_title: str | None = None
		self.live_x_label = "Simulation time (s)"
		self.live_y_label = "Value"
		self.live_y_limits: tuple[float, float] | None = None
		self._live_refresh_counter = 0
		self.LIVE_REFRESH_INTERVAL = 6
		self._live_labels: tuple[str, ...] | None = None

		self.redraw()

	def set_live_data_source(
		self,
		data_source: Callable[
			[],
			tuple[Sequence[float], dict[str, Sequence[float]]],
		],
		*,
		title: str,
		x_label: str = "Simulation time (s)",
		y_label: str = "Value",
		y_limits: tuple[float, float] | None = None,
		revision_source: Callable[[], int] | None = None,
	) -> None:
		self.data_source = data_source
		self.revision_source = revision_source
		self._last_data_revision: int | None = None
		self.live_title = title
		self.live_x_label = x_label
		self.live_y_label = y_label
		self.live_y_limits = y_limits
		self._live_refresh_counter = self.LIVE_REFRESH_INTERVAL
		self.ax.set_title(title)
		self.ax.set_xlabel(x_label)
		self.ax.set_ylabel(y_label)
		if y_limits is not None:
			self.ax.set_ylim(*y_limits)
		self.fig.tight_layout()
		self.redraw()

	def _on_update(self, frame_data: FrameData):
		if self.data_source is None:
			return
		self._live_refresh_counter += 1
		if self._live_refresh_counter < self.LIVE_REFRESH_INTERVAL:
			return
		self._live_refresh_counter = 0
		data_revision = (
			self.revision_source()
			if self.revision_source is not None
			else None
		)
		if (
			self.revision_source is not None
			and data_revision == self._last_data_revision
		):
			return

		times, series = self.data_source()
		existing_lines = {
			line.get_label(): line
			for line in self.ax.lines
		}
		for label in tuple(existing_lines):
			if label not in series:
				existing_lines[label].remove()

		for label, values in series.items():
			line = existing_lines.get(label)
			if line is None:
				self.ax.plot(times[:len(values)], values, label=label)
			else:
				line.set_data(times[:len(values)], values)

		labels = tuple(series)
		if labels != self._live_labels:
			legend = self.ax.get_legend()
			if legend is not None:
				legend.remove()
			if series:
				self.ax.legend(loc="upper right", fontsize=8)
			self._live_labels = labels
		self.ax.relim()
		self.ax.autoscale_view()
		if self.live_y_limits is not None:
			self.ax.set_ylim(*self.live_y_limits)
		self.redraw()
		self._last_data_revision = data_revision

	def _on_adoption(self):
		self._update_size()

	def _update_size(self):
		if not hasattr(self, "parent"):
			return

		width = self.parent.get_content_width()
		width = max(1, width)
		if self.rect.width == width and self.rect.height == self.height:
			return

		self.size = (width, self.height)
		self.rect.size = self.size
		self.fig.set_size_inches(width / self.dpi, self.height / self.dpi, forward=False)
		self.fig.tight_layout()
		self.redraw()

	def redraw(self):
		self.canvas.draw()
		raw_data = self.canvas.buffer_rgba()
		size = self.canvas.get_width_height()
		self.plot_surface = pygame.image.frombuffer(
			raw_data,
			size,
			"RGBA",
		)
		if pygame.display.get_surface() is not None:
			self.plot_surface = self.plot_surface.convert()

	def draw(self, surf: pygame.Surface):
		dx, dy = self.offset
		self.rect.move_ip(dx, dy)

		if self.plot_surface:
			surf.blit(self.plot_surface, self.rect.topleft)

		self.rect.move_ip(-dx, -dy)

		super().draw(surf)