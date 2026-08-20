import pygame
import matplotlib
# Force matplotlib to not use any Xwindows backend. 
# This must be called before importing FigureCanvasAgg or pyplot.
matplotlib.use("Agg") 

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from ..core import Component

class MatplotlibComponent(Component):
    def __init__(self, rel_pos, size, anchor=None, dock=None, dpi=100):
        super().__init__(rel_pos, size, anchor, dock)
        
        self.dpi = dpi
        
        # Convert Pygame pixel size to Matplotlib inches
        fig_width = self.size[0] / self.dpi
        fig_height = self.size[1] / self.dpi
        
        # Initialize Matplotlib Figure and Canvas
        self.fig = Figure(figsize=(fig_width, fig_height), dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        
        # Cache for the Pygame surface
        self.plot_surface = None
        
        # Format the plot slightly to fit well in UI (optional)
        self.fig.tight_layout()
        
        # Generate the initial empty plot
        self.redraw()

    def redraw(self):
        """
        Renders the Matplotlib Figure and updates the cached Pygame Surface.
        Call this manually ONLY when your plot data actually changes.
        Do NOT call this every frame in update() as it is very slow.
        """
        # Draw the canvas internally
        self.canvas.draw()
        
        # Get the RGBA buffer from the renderer
        raw_data = self.canvas.buffer_rgba()
        size = self.canvas.get_width_height()
        
        # Convert the raw buffer to a Pygame Surface
        self.plot_surface = pygame.image.frombuffer(raw_data, size, "RGBA")

    def draw(self, surf):
        # Draw the cached Matplotlib surface at the component's calculated absolute position
        if self.plot_surface:
            surf.blit(self.plot_surface, self.rect.topleft)
            
        # Draw any potential children added to this component
        super().draw(surf)