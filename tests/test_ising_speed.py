import unittest
from types import SimpleNamespace

from src.settings import Setting
from src.simulations.ising import IsingSimulation


class FakeUniform:
    value = None


class FakeComputeProgram(dict):
    def __init__(self):
        super().__init__(
            (name, FakeUniform())
            for name in (
                "u_grid_size",
                "u_temperature",
                "u_coupling",
                "u_external_field",
                "u_parity",
                "u_step",
            )
        )
        self.run_count = 0

    def run(self, **_kwargs):
        self.run_count += 1


class FakeTexture:
    def use(self, location):
        pass

    def bind_to_image(self, unit, *, read, write):
        pass


def make_simulation():
    simulation = object.__new__(IsingSimulation)
    simulation.schema = {
        "temperature": SimpleNamespace(setting=Setting(2.269)),
        "coupling": SimpleNamespace(setting=Setting(1.0)),
        "external_field": SimpleNamespace(setting=Setting(0.0)),
    }
    simulation.grid_width = Setting(16)
    simulation.grid_height = Setting(16)
    simulation._compute_program = FakeComputeProgram()
    simulation.grid_a = FakeTexture()
    simulation.grid_b = FakeTexture()
    simulation._current_grid = 0
    simulation._step_count = 0
    simulation._sweep_accumulator = 0.0
    simulation.ctx = SimpleNamespace(memory_barrier=lambda: None)
    return simulation


class TestIsingSimulationSpeed(unittest.TestCase):
    def test_half_speed_runs_half_as_many_sweeps(self):
        simulation = make_simulation()

        for _ in range(60):
            simulation.step(0.5 / 60)

        self.assertEqual(simulation._step_count, 30)
        self.assertEqual(simulation._compute_program.run_count, 60)

    def test_double_speed_runs_two_sweeps_per_sixtieth_second(self):
        simulation = make_simulation()

        simulation.step(2 / 60)

        self.assertEqual(simulation._step_count, 2)
        self.assertEqual(simulation._compute_program.run_count, 4)


if __name__ == "__main__":
    unittest.main()
