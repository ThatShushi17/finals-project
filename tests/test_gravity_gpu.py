import unittest

import moderngl
import numpy as np
import pygame

from src.engine.simulation.three.n_parts.solar_system import G_AU
from src.enums import Accents
from src.simulations.gravity import GravitySimulation


class FakeColorScheme:
    def accent(self, accent: Accents) -> pygame.Color:
        return pygame.Color(100, 140, 240)

    def bg_bold(self) -> pygame.Color:
        return pygame.Color(20, 24, 32)


class TestGravityGpuIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pygame.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 4)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK,
            pygame.GL_CONTEXT_PROFILE_CORE,
        )
        pygame.display.set_mode((1, 1), pygame.OPENGL | pygame.DOUBLEBUF)

    @classmethod
    def tearDownClass(cls) -> None:
        pygame.quit()

    def test_gpu_velocity_verlet_matches_numpy_reference(self):
        context = moderngl.create_context()
        simulation = None
        try:
            schema = GravitySimulation.get_schema()
            simulation = GravitySimulation(
                context,
                schema,
                FakeColorScheme(),  # type: ignore[arg-type]
            )
            dt = 0.0005
            initial_positions = simulation.positions.copy()
            initial_velocities = simulation.velocities.copy()
            softening = float(schema["softening"].setting.value)
            acceleration = GravitySimulation._calculate_accelerations(
                initial_positions,
                simulation.masses,
                G_AU,
                softening,
            )
            expected_positions = (
                initial_positions
                + initial_velocities * dt
                + 0.5 * acceleration * dt**2
            )
            next_acceleration = GravitySimulation._calculate_accelerations(
                expected_positions,
                simulation.masses,
                G_AU,
                softening,
            )
            expected_velocities = initial_velocities + 0.5 * (
                acceleration + next_acceleration
            ) * dt

            simulation.apply_law(dt)

            np.testing.assert_allclose(
                simulation.positions,
                expected_positions,
                atol=2e-6,
            )
            np.testing.assert_allclose(
                simulation.velocities,
                expected_velocities,
                atol=2e-6,
            )
        finally:
            if simulation is not None:
                simulation.cleanup()
            context.release()


if __name__ == "__main__":
    unittest.main()
