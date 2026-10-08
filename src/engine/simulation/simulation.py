import pygame
import glm
from .schema import SimulationSchema

class Simulation:
    """Base class for all simulations."""
    def __init__(self, ctx, config: dict = None):
        self.ctx = ctx
        self.config = config or {} # Store configuration state
        self.camera_distance, self.camera_pitch, self.camera_yaw = 4.5, 0.5, 0.0
        self.fbo = None
        self.color_tex = None
        self.depth_rb = None

    @classmethod
    def get_schema(cls) -> SimulationSchema:
        """Override in subclass to expose UI configuration parameters."""
        return SimulationSchema([])

    def step(self, dt):
        pass

    def draw_simulation(self, view_proj):
        """Override in subclass to execute drawing calls."""
        pass

    def process_mouse(self, dx, dy, scroll_dy):
        self.camera_yaw -= dx * 0.007
        self.camera_pitch += dy * 0.007
        self.camera_pitch = max(-1.4, min(1.4, self.camera_pitch))

        if scroll_dy != 0:
            self.camera_distance = max(1.0, min(20.0, self.camera_distance - scroll_dy * 0.5))

    def render(self, surf: pygame.Surface, frame_rect=(0, 0, 700, 450)):
        """
        Main interface called by Frame. Prepares FBO, delegates draw call 
        to subclass, and blits result to the Pygame Surface.
        """
        width, height = surf.get_size()
        if width <= 0 or height <= 0:
            return

        # 1. Update FBO size if needed
        if self.fbo is None or self.fbo.size != (width, height):
            self._resize_fbo(width, height)

        # 2. Bind and Clear FBO
        self.fbo.use()
        self.fbo.clear(0.1, 0.1, 0.1, 1.0)

        # 3. Delegate specific simulation rendering
        view_proj = self._get_view_projection(width, height)
        self.draw_simulation(view_proj, frame_rect)

        # 4. Copy FBO texture to Pygame Surface
        data = self.fbo.read(components=4)
        img = pygame.image.frombuffer(data, (width, height), 'RGBA')
        img = pygame.transform.flip(img, False, True)
        surf.blit(img, (0, 0))

        # 5. Restore screen rendering context
        self.ctx.screen.use()

    def cleanup(self):
        if self.fbo: self.fbo.release()
        if self.color_tex: self.color_tex.release()
        if self.depth_rb: self.depth_rb.release()

    def _get_view_projection(self, width: int, height: int):
        """Calculates combined 3D View-Projection matrix."""
        cam_x = self.camera_distance * glm.cos(self.camera_pitch) * glm.sin(self.camera_yaw)
        cam_y = self.camera_distance * glm.sin(self.camera_pitch)
        cam_z = self.camera_distance * glm.cos(self.camera_pitch) * glm.cos(self.camera_yaw)

        aspect = width / height if height > 0 else 1.0
        projection = glm.perspective(glm.radians(45.0), aspect, 0.1, 100.0)
        view = glm.lookAt(glm.vec3(cam_x, cam_y, cam_z), glm.vec3(0.0, 0.0, 0.0), glm.vec3(0.0, 1.0, 0.0))
        return projection * view

    def _resize_fbo(self, width: int, height: int):
        """Reallocates Framebuffer resources when dimensions change."""
        if self.fbo: self.fbo.release()
        if self.color_tex: self.color_tex.release()
        if self.depth_rb: self.depth_rb.release()

        self.color_tex = self.ctx.texture((width, height), 4)
        self.depth_rb = self.ctx.depth_renderbuffer((width, height))
        self.fbo = self.ctx.framebuffer(self.color_tex, self.depth_rb)