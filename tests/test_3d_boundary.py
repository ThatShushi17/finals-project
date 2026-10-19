import unittest

import numpy as np

from src.engine.simulation.three.simulation_3d import (
    Simulation3D,
    bounding_box_vertices,
)
from src.engine.simulation.two.simulation_2d import Simulation2D
from src.engine.simulation.two.grid.continuous import ContinuousGridSimulation
from src.engine.simulation.two.grid.discrete import DiscreteGridSimulation
from src.simulations.fluid_dynamics import FluidDynamicsSimulation


class TestSimulationBoundingBoxes(unittest.TestCase):
    def test_3d_bounds_are_12_world_space_edges(self):
        bounds = ((-2.0, -3.0, -4.0), (2.0, 3.0, 4.0))
        vertices = bounding_box_vertices(bounds)

        self.assertEqual(vertices.shape, (24, 3))
        self.assertEqual(len(np.unique(vertices, axis=0)), 8)
        for start, end in vertices.reshape((12, 2, 3)):
            self.assertEqual(np.count_nonzero(start != end), 1)
            for axis, limits in enumerate(((-2.0, 2.0), (-3.0, 3.0), (-4.0, 4.0))):
                self.assertIn(start[axis], limits)
                self.assertIn(end[axis], limits)
        self.assertIn("u_view_projection * vec4(in_position, 1.0)", Simulation3D.BOUNDING_BOX_VERTEX_SHADER)
        self.assertIn("frag_color = u_color", Simulation3D.BOUNDING_BOX_FRAGMENT_SHADER)
        self.assertNotIn("smoothstep", Simulation3D.BOUNDING_BOX_FRAGMENT_SHADER)

    def test_3d_simulations_use_their_spatial_bounds(self):
        from src.simulations.boids import BoidsSimulation
        from src.simulations.gravity import GravitySimulation

        self.assertEqual(
            BoidsSimulation.WORLD_BOUNDS,
            ((-2.0, -2.0, -2.0), (2.0, 2.0, 2.0)),
        )
        self.assertEqual(
            GravitySimulation.WORLD_BOUNDS,
            ((-35.0, -35.0, -35.0), (35.0, 35.0, 35.0)),
        )

    def test_2d_render_shaders_use_a_solid_one_pixel_edge(self):
        shader_files = (
            DiscreteGridSimulation.FRAGMENT_SHADER,
            ContinuousGridSimulation.FRAGMENT_SHADER,
            FluidDynamicsSimulation.FRAGMENT_SHADER,
        )
        for shader in shader_files:
            with self.subTest(shader=shader[:40]):
                self.assertIn("u_outline_color", shader)
                self.assertIn("boundary_distance <= 0.5", shader)
                self.assertNotIn("u_boundary_softness", shader)
                self.assertNotIn("u_boundary_strength", shader)

    def test_old_accent_border_overlay_is_removed(self):
        self.assertNotIn("_draw_boundary", Simulation3D.__dict__)
        self.assertNotIn("_boundary_overlay", Simulation3D.__dict__)
        self.assertNotIn("_set_boundary_uniforms", Simulation2D.__dict__)


if __name__ == "__main__":
    unittest.main()
