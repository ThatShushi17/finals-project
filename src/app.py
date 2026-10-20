from pathlib import Path

import moderngl as mgl
import pygame

from .settings import Settings
from .engine.ui import MenuSystem, UIBuilder, UIRenderer, FontHandler, ColorScheme
from .engine.frame_data import FrameData

from .types import Dual, FiendCallback
# from .enums import Settings

class App:
    def __init__(self, window_size: Dual, exit_callback: FiendCallback):
        cwd = Path(__file__).resolve().parent
        root = cwd.parent
        self.settings = Settings(root / "data" / "misc" / "usersettings.csv")
        self.screenshot_dir = root / "data/misc/screenshots"
        
        def exit_app():
            self.ui_builder.cleanup_active_simulation()
            self.settings.write_csv()
            exit_callback()

        self.exit_callback = exit_app

        self.ctx = mgl.create_context()
        self.clock = pygame.time.Clock()
        self.frame_data = FrameData()
        self.ui_tex = self.ctx.texture(window_size, 4)
        self.ui_tex.use(0)
    
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        self.font_handler = FontHandler(  # TODO: sidequest dropdown class -> add to settings
            default_font=FontHandler.font_dir / "Roboto-Regular.ttf",
            default_bold=FontHandler.font_dir / "Roboto-Bold.ttf",
            default_size=22
        )
        self.color_scheme = ColorScheme(
            settings=self.settings
        )

        self.menu_system = MenuSystem(
            frame_data=self.frame_data,
            font_handler=self.font_handler,
            color_scheme=self.color_scheme,
            window_size=window_size
        )
        
        self.ui_builder = UIBuilder(self.menu_system, self.ctx)
        self.ui_renderer = UIRenderer(self.ctx, self.ui_tex)
        self.ui_builder.create_ui(self.exit_callback, self.settings)

    def tick(self) -> None:
        dt = self.clock.tick(self.settings.fps.value) / 1000
        self.frame_data.update(dt)
        screenshot_requested = False

        for event in self.frame_data.events:
            if event.type == pygame.QUIT:
                self.exit_callback()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                screenshot_requested = True
    
        self.menu_system.update()
        self.ui_builder.cleanup_inactive_simulation()
        ui_surf = self.menu_system.render()
        ui_buffer = ui_surf.get_buffer()
        self.ui_tex.write(ui_buffer)
    
        self.ctx.clear(0.0, 0.0, 0.0)
    
        self.ui_tex.use(0)
        self.ui_renderer.vao.render(mgl.TRIANGLE_STRIP)
    
        pygame.display.flip()
        if screenshot_requested:
            self._save_screenshot()

    def _save_screenshot(self) -> None:
        width, height = self.ctx.screen.size
        pixels = self.ctx.screen.read(
            viewport=(0, 0, width, height),
            components=3,
            alignment=1,
        )
        image = pygame.image.frombytes(pixels, (width, height), "RGB")
        image = pygame.transform.flip(image, False, True)

        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_number = len(tuple(self.screenshot_dir.glob("screenshot_*.png"))) + 1
        pygame.image.save(image, self.screenshot_dir / f"screenshot_{screenshot_number}.png")
