import numpy as np
import pygame
import moderngl as mgl

from .ui import UIBuilder, MenuSystem, FrameData
from .shader_handler import load_shader_pair

class App:
    def __init__(self, window_size):
        exit_callback = lambda *args, **kwargs: setattr(self, "running", False)

        self.ctx = mgl.create_context()
        self.clock = pygame.time.Clock()
        self.frame_data = FrameData()
        self.menu_system = MenuSystem(self.frame_data, window_size)
        self.ui_builder = UIBuilder(self.menu_system, self.ctx)
        self.ui_builder.create_ui(exit_callback)

        self.vert_src, self.frag_src = load_shader_pair("ui/vert.vert", "ui/frag.frag")
        self.ui_prog = self.ctx.program(vertex_shader=self.vert_src, fragment_shader=self.frag_src)
        self.ui_tex = self.ctx.texture(window_size, 4)

        self.verts = np.array([
            -1,  1, 0, 0,
            -1, -1, 0, 1,
            1,  1, 1, 0,
            1, -1, 1, 1
        ], dtype="f4")
        self.vbo = self.ctx.buffer(self.verts)
        self.vao = self.ctx.vertex_array(self.ui_prog, [(self.vbo, "2f 2f", "in_vert", "in_texcoord")])

        self.running = True

    def tick(self):
        self.frame_data.update()

        for event in self.frame_data.events:
            if event.type == pygame.QUIT:
                self.running = False
    
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q and (event.mod & pygame.KMOD_LCTRL):
                    self.running = False
    
        self.menu_system.update()
        ui_surf = self.menu_system.render()
        ui_buffer = ui_surf.get_buffer()
        self.ui_tex.write(ui_buffer)
        del ui_buffer
    
        self.ctx.clear(0.1, 0.1, 0.2)
    
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        
        self.ui_tex.use(0)
        self.vao.render(mgl.TRIANGLE_STRIP)
    
        pygame.display.flip()
        self.clock.tick(60)