import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame

from src.app import App


class TestAppScreenshot(unittest.TestCase):
    def test_f11_saves_the_rendered_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            screenshot_dir = Path(directory)
            (screenshot_dir / "screenshot_1.png").touch()
            app = object.__new__(App)
            app.clock = Mock()
            app.clock.tick.return_value = 16
            app.__dict__.update(
                settings=SimpleNamespace(fps=SimpleNamespace(value=60)),
                frame_data=SimpleNamespace(
                    events=[pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11)],
                    update=Mock(),
                ),
            )
            app.ctx = Mock()
            app.ctx.screen.size = (2, 2)
            app.ctx.screen.read.return_value = bytes(
                (
                    0, 0, 255, 255, 255, 0,
                    255, 0, 0, 0, 255, 0,
                )
            )
            app.menu_system = Mock()
            app.menu_system.render.return_value.get_buffer.return_value = b""
            app.ui_builder = Mock()
            app.ui_tex = Mock()
            app.ui_renderer = Mock()
            app.screenshot_dir = screenshot_dir

            with patch("pygame.display.flip"):
                app.tick()

            screenshot_path = screenshot_dir / "screenshot_2.png"
            self.assertTrue(screenshot_path.exists())
            saved_image = pygame.image.load(screenshot_path)
            self.assertEqual(saved_image.get_at((0, 0))[:3], (255, 0, 0))
            self.assertEqual(saved_image.get_at((1, 0))[:3], (0, 255, 0))
            app.ctx.screen.read.assert_called_once()


if __name__ == "__main__":
    unittest.main()
