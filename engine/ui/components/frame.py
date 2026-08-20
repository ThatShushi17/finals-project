import pygame
from ..core import Component, FrameData

class Frame(Component):
    def __init__(self, rel_pos, size, simulation=None, anchor=None, dock=None):
        super().__init__(rel_pos, size, anchor=anchor, dock=dock)
        self.simulation = simulation
        self.background_color = (39, 39, 39)
        self.border_color = (106, 73, 255)
        self.border_width = 2
        
        # Internal state ported from deprecated Viewport
        self.is_hovered = False
        self.is_dragging = False
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_scroll = 0
    
    def _on_update(self, frame_data: FrameData):
        self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)
        
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_scroll = 0
        
        for event in frame_data.events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.is_hovered:
                    if event.button == 1:
                        self.is_dragging = True
                    elif event.button == 4:
                        self.mouse_scroll = 1
                    elif event.button == 5:
                        self.mouse_scroll = -1
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.is_dragging = False
            elif event.type == pygame.MOUSEMOTION:
                if self.is_dragging:
                    self.mouse_dx, self.mouse_dy = event.rel

        if self.simulation is not None:
            if self.mouse_dx != 0 or self.mouse_dy != 0 or self.mouse_scroll != 0:
                self.simulation.process_mouse(self.mouse_dx, self.mouse_dy, self.mouse_scroll)
                
            # Safely fetch dt based on your FrameData implementation
            dt = getattr(frame_data, 'delta_time', getattr(frame_data, 'dt', 0.016))
            self.simulation.step(dt)

    def draw(self, surf):
        clipped_rect = self.rect.clip(surf.get_rect())
        if clipped_rect.width <= 0 or clipped_rect.height <= 0:
            return

        frame_surf = surf.subsurface(clipped_rect)
        frame_surf.fill(self.background_color)

        if self.simulation is not None:
            self.simulation.render(frame_surf, frame_rect=clipped_rect)

        if self.border_color is not None:
            pygame.draw.rect(
                surf,
                self.border_color,
                self.rect,
                self.border_width,
            )

        super().draw(surf)