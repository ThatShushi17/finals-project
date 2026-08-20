import unittest
import numpy as np
import pandas as pd
import pygame
import moderngl as mgl


class TestEnvironment(unittest.TestCase):
    """Verify all required libraries are installed and working."""

    def test_numpy_import(self):
        """Test NumPy can be imported and has version info."""
        self.assertIsNotNone(np.__version__)
        self.assertGreaterEqual(tuple(map(int, np.__version__.split('.')[:2])), (2, 0))

    def test_pandas_import(self):
        """Test Pandas can be imported and has version info."""
        self.assertIsNotNone(pd.__version__)

    def test_pygame_initialization(self):
        """Test Pygame can initialize and setup OpenGL context."""
        pygame.init()
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            
            pygame.display.set_mode((100, 100), pygame.OPENGL | pygame.DOUBLEBUF)
            self.assertIsNotNone(pygame.display.get_surface())
        finally:
            pygame.quit()

    def test_moderngl_context_creation(self):
        """Test ModernGL can create an OpenGL 4.3 context and retrieve vendor info."""
        pygame.init()
        try:
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
            pygame.display.gl_set_attribute(pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE)
            
            pygame.display.set_mode((100, 100), pygame.OPENGL | pygame.DOUBLEBUF)
            ctx = mgl.create_context()
            
            # Verify context was created successfully
            self.assertIsNotNone(ctx)
            self.assertIsNotNone(ctx.info['GL_VENDOR'])
            self.assertTrue(len(ctx.info['GL_VENDOR']) > 0)
        finally:
            ctx.release()
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
