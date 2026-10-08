import pygame
import moderngl as mgl

from collections.abc import Callable

from .engine.ui import MenuSystem, UIBuilder, UIRenderer
from .engine.frame_data import FrameData

from .types import Dual

class App:
    def __init__(self, window_size: Dual, exit_callback: Callable[[], None]):
        self.exit_callback = exit_callback
        self.fps = 60

        self.ctx = mgl.create_context()
        self.clock = pygame.time.Clock()
        self.frame_data = FrameData()
        self.ui_tex = self.ctx.texture(window_size, 4)
        self.ui_tex.use(0)
    
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        self.menu_system = MenuSystem(self.frame_data, window_size)
        self.ui_builder = UIBuilder(self.menu_system, self.ctx)
        self.ui_renderer = UIRenderer(self.ctx, self.ui_tex)
        self.ui_builder.create_ui(exit_callback)

    def tick(self) -> None:
        self.frame_data.update()

        for event in self.frame_data.events:
            if event.type == pygame.QUIT:
                self.exit_callback()
    
        self.menu_system.update()
        ui_surf = self.menu_system.render()
        ui_buffer = ui_surf.get_buffer()
        self.ui_tex.write(ui_buffer)
    
        self.ctx.clear(0.1, 0.1, 0.2)
    
        self.ui_renderer.vao.render(mgl.TRIANGLE_STRIP)
    
        pygame.display.flip()
        self.clock.tick(self.fps)

# TODO: ColorScheme class instead of littering properties everywhere.