import unittest
import pygame as pg
import moderngl as mgl
import numpy as np
import struct


class TestComputeShader(unittest.TestCase):
    """Test GPU compute shader compilation and execution."""

    @classmethod
    def setUpClass(cls):
        """Initialize Pygame once for all tests in this class."""
        pg.init()

    @classmethod
    def tearDownClass(cls):
        """Cleanup Pygame after all tests."""
        pg.quit()

    def setUp(self):
        """Create OpenGL context for each test."""
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MAJOR_VERSION, 4)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_MINOR_VERSION, 3)
        pg.display.gl_set_attribute(pg.GL_CONTEXT_PROFILE_MASK, pg.GL_CONTEXT_PROFILE_CORE)
        pg.display.set_mode((1, 1), pg.OPENGL | pg.DOUBLEBUF)
        self.ctx = mgl.create_context()

    def tearDown(self):
        """Release OpenGL context after each test."""
        if self.ctx:
            self.ctx.release()

    def test_compute_shader_compilation(self):
        """Test that a compute shader can be compiled."""
        compute_shader_code = """
        #version 430

        layout(local_size_x = 4, local_size_y = 1, local_size_z = 1) in;

        layout(std430, binding = 0) buffer DataBuffer {
            float data[];
        };

        void main() {
            uint id = gl_LocalInvocationID.x;
            data[id] = data[id] * data[id];
        }
        """
        
        cs = self.ctx.compute_shader(compute_shader_code)
        self.assertIsNotNone(cs)

    def test_compute_shader_execution(self):
        """Test compute shader execution with data validation."""
        compute_shader_code = """
        #version 430

        layout(local_size_x = 4, local_size_y = 1, local_size_z = 1) in;

        layout(std430, binding = 0) buffer DataBuffer {
            float data[];
        };

        void main() {
            uint id = gl_LocalInvocationID.x;
            data[id] = data[id] * data[id];
        }
        """
        
        cs = self.ctx.compute_shader(compute_shader_code)
        
        # Prepare test data
        input_data = np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32)
        buffer = self.ctx.buffer(input_data.tobytes())
        buffer.bind_to_storage_buffer(binding=0)
        
        # Execute compute shader
        cs.run(group_x=1, group_y=1, group_z=1)
        
        # Read back results
        output_bytes = buffer.read()
        output_data = struct.unpack('4f', output_bytes)
        
        # Verify computation: [1, 2, 3, 4] -> [1, 4, 9, 16]
        expected = [1.0, 4.0, 9.0, 16.0]
        self.assertTrue(np.allclose(output_data, expected))
        
        # Cleanup
        buffer.release()
        cs.release()


if __name__ == "__main__":
    unittest.main()
