import pygame
import matplotlib

matplotlib.use("Agg") 
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

from ....types import Dual
from ....enums import Position

from ..component import Component

class Plot(Component):
    def __init__(
        self,
        relative_position: Dual,
        size: Dual,
        dpi: int = 100,
        anchor: Position = Position.CENTER,
        dock: Position = Position.CENTER
    ):
        super().__init__(relative_position, size, anchor, dock)
        self.dpi = dpi
        
        fig_width = self.size[0] / self.dpi
        fig_height = self.size[1] / self.dpi
        
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.plot_surface = None

        self.fig.tight_layout()
        
        self.redraw()

    def redraw(self):
        self.canvas.draw()
        raw_data = self.canvas.buffer_rgba()
        size = self.canvas.get_width_height()
        self.plot_surface = pygame.image.frombuffer(raw_data, size, "RGBA")

    def draw(self, surf: pygame.Surface):
        if self.plot_surface:
            surf.blit(self.plot_surface, self.rect.topleft)

        super().draw(surf)