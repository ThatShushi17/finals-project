import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from collections import deque
from types import SimpleNamespace

from src.engine.simulation.two.grid.continuous import ContinuousGridSimulation
from src.engine.simulation.two.simulation_2d import Simulation2D
from src.engine.simulation.simulation import Simulation
from src.settings import Setting, SliderDetails, CheckboxDetails, InputDetails
from src.simulations.reaction_diffusion import ReactionDiffusionSimulation


class FakeUniform:
    def __init__(self):
        self.value = None


class FakeComputeProgram(dict):
    def __init__(self):
        super().__init__()
        self["u_grid_size"] = FakeUniform()
        self["u_diffusion_a"] = FakeUniform()
        self["u_diffusion_b"] = FakeUniform()
        self["u_feed_rate"] = FakeUniform()
        self["u_kill_rate"] = FakeUniform()
        self["u_time_step"] = FakeUniform()
        self.time_steps = []

    def run(self, **_kwargs):
        self.time_steps.append(self["u_time_step"].value)


class FakeTexture:
    def use(self, location):
        pass

    def bind_to_image(self, unit, *, read, write):
        pass


class TestReactionDiffusion(unittest.TestCase):
    def test_data_collection_waits_for_configured_simulated_time(self):
        schema = {
            "data_collection_interval": SliderDetails(
                "Data Collection Interval",
                setting=Setting(0.1),
                lower_bound=0.1,
                upper_bound=5.0,
                initial_only=True,
            ),
        }
        simulation = Simulation(None, schema, None)
        simulation.get_metrics = lambda: {}

        simulation.advance(0.04)
        simulation.advance(0.04)
        self.assertEqual(list(simulation.history_times), [])

        simulation.advance(0.02)

        self.assertAlmostEqual(list(simulation.history_times)[0], 0.1)

    def test_advance_records_live_settings_on_each_scaled_timestep(self):
        class RecordingSimulation(Simulation):
            def __init__(self, schema):
                super().__init__(None, schema, None)
                self.received_dt = []

            def step(self, dt):
                self.received_dt.append(dt)

        schema = {
            "simulation_speed": SliderDetails(
                "Simulation Speed",
                setting=Setting(2.0),
                lower_bound=0.1,
                upper_bound=10.0,
            ),
            "data_collection_interval": SliderDetails(
                "Data Collection Interval",
                setting=Setting(0.01),
                lower_bound=0.1,
                upper_bound=5.0,
                initial_only=True,
            ),
            "feed_rate": SliderDetails(
                "Feed Rate",
                setting=Setting(0.2),
                lower_bound=0.0,
                upper_bound=0.1,
            ),
            "initial_grid": CheckboxDetails(
                "Initial Grid",
                setting=Setting(False),
                initial_value=False,
                initial_only=True,
            ),
        }
        simulation = RecordingSimulation(schema)
        simulation.advance(0.02)
        self.assertEqual(simulation.received_dt, [0.02])
        self.assertEqual(list(simulation.history_times), [0.02])
        self.assertAlmostEqual(
            simulation.setting_history["Simulation Speed"][0],
            (2.0 - 0.1) / (10.0 - 0.1),
        )
        self.assertEqual(list(simulation.setting_history["Feed Rate"]), [1.0])
        self.assertNotIn("Initial Grid", simulation.setting_history)
        self.assertNotIn("Data Collection Interval", simulation.setting_history)

    def test_setting_series_only_returns_live_schema_settings(self):
        simulation = Simulation(
            None,
            {
                "live_setting": SliderDetails(
                    "Live Setting",
                    setting=Setting(0.5),
                    lower_bound=0.0,
                    upper_bound=1.0,
                ),
                "initial_setting": SliderDetails(
                    "Initial Setting",
                    setting=Setting(1.0),
                    lower_bound=0.0,
                    upper_bound=1.0,
                    initial_only=True,
                ),
            },
            None,
        )
        simulation.setting_history = {
            "Live Setting": deque([0.5]),
            "Initial Setting": deque([1.0]),
            "Removed Setting": deque([0.25]),
        }

        self.assertEqual(
            simulation.get_setting_series(),
            {"Live Setting": [0.5]},
        )

    def test_cleanup_exports_enabled_recording_to_simulation_readings_folder(self):
        schema = {
            "record_csv": CheckboxDetails(
                "Record Gathered Data",
                setting=Setting(True),
                initial_value=False,
                initial_only=True,
            ),
            "csv_filename": InputDetails(
                "CSV Output Name",
                setting=Setting("run-one"),
                placeholder_text="Enter a name",
                initial_only=True,
            ),
            "simulation_speed": SliderDetails(
                "Simulation Speed",
                setting=Setting(2.0),
                lower_bound=0.1,
                upper_bound=10.0,
            ),
        }
        simulation = Simulation(None, schema, None)
        simulation.simulation_name = "example_sim"
        simulation.history_times.append(0.5)
        simulation.setting_history["Simulation Speed"] = deque([0.2])
        simulation.metric_history["Metric"] = deque([3.0])

        with TemporaryDirectory() as directory:
            simulation.READINGS_ROOT = Path(directory) / "readings"
            simulation.cleanup()
            output_path = simulation.READINGS_ROOT / "example_sim" / "run-one.csv"
            self.assertTrue(output_path.is_file())

            import pandas as pd

            exported = pd.read_csv(output_path)
            self.assertEqual(
                list(exported.columns),
                ["Simulation time (s)", "Simulation Speed", "Metric"],
            )
            self.assertEqual(exported.iloc[0].tolist(), [0.5, 0.2, 3.0])

    def test_cleanup_does_not_write_csv_when_recording_is_disabled(self):
        simulation = Simulation(
            None,
            {
                "record_csv": CheckboxDetails(
                    "Record Gathered Data",
                    setting=Setting(False),
                    initial_value=False,
                    initial_only=True,
                ),
                "csv_filename": InputDetails(
                    "CSV Output Name",
                    setting=Setting("run-one"),
                    placeholder_text="Enter a name",
                    initial_only=True,
                ),
            },
            None,
        )

        with TemporaryDirectory() as directory:
            simulation.READINGS_ROOT = Path(directory) / "readings"
            simulation.cleanup()
            self.assertFalse(simulation.READINGS_ROOT.exists())

    def test_simulation_speed_reads_live_schema_setting(self):
        simulation = object.__new__(Simulation)
        speed = Setting(2.5)
        simulation.schema = {
            "simulation_speed": SimpleNamespace(setting=speed),
        }

        self.assertEqual(simulation.simulation_speed, 2.5)

        speed.value = 0.5
        self.assertEqual(simulation.simulation_speed, 0.5)

    def test_continuous_grid_simulation_extends_simulation_2d(self):
        self.assertTrue(issubclass(ContinuousGridSimulation, Simulation2D))
        self.assertTrue(
            issubclass(ReactionDiffusionSimulation, ContinuousGridSimulation)
        )

    def test_initial_grid_has_two_bounded_chemical_fields_and_seed(self):
        grid = ReactionDiffusionSimulation.create_initial_grid(80, 60)

        self.assertEqual(grid.shape, (60, 80, 2))
        self.assertEqual(grid.dtype, np.float32)
        self.assertTrue(np.isfinite(grid).all())
        self.assertTrue(np.all((grid >= 0.0) & (grid <= 1.0)))
        self.assertTrue(np.all(grid[0, 0] == (1.0, 0.0)))
        self.assertEqual(grid[30, 40, 0], 0.5)
        self.assertGreater(grid[30, 40, 1], 0.0)

    def test_initial_patterns_create_distinct_valid_grids(self):
        patterns = ("central_seed", "multiple_spots", "stripes", "rings")
        grids = [
            ReactionDiffusionSimulation.create_initial_grid(80, 60, pattern)
            for pattern in patterns
        ]

        for grid in grids:
            self.assertEqual(grid.shape, (60, 80, 2))
            self.assertTrue(np.isfinite(grid).all())
            self.assertTrue(np.all((grid >= 0.0) & (grid <= 1.0)))
        self.assertFalse(np.array_equal(grids[0], grids[1]))
        self.assertFalse(np.array_equal(grids[1], grids[2]))
        self.assertFalse(np.array_equal(grids[2], grids[3]))

    def test_simulation_uses_selected_initial_pattern(self):
        simulation = object.__new__(ReactionDiffusionSimulation)
        simulation.schema = {
            "initial_pattern": SimpleNamespace(setting=Setting("stripes")),
        }

        grid = simulation.get_initial_grid(80, 60)
        expected = ReactionDiffusionSimulation.create_initial_grid(
            80,
            60,
            "stripes",
        )
        np.testing.assert_array_equal(grid, expected)

    def test_unknown_initial_pattern_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown reaction-diffusion"):
            ReactionDiffusionSimulation.create_initial_grid(80, 60, "unknown")

    def test_schema_exposes_grid_and_reaction_parameters(self):
        schema = ReactionDiffusionSimulation.get_schema()

        self.assertTrue({
            "grid_width",
            "grid_height",
            "diffusion_a",
            "diffusion_b",
            "feed_rate",
            "kill_rate",
            "initial_pattern",
        }.issubset(schema))
        self.assertTrue(schema["initial_pattern"].initial_only)
        self.assertEqual(schema["initial_pattern"].default_value, "central_seed")

    def test_data_collection_interval_is_initial_only_and_persisted(self):
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from src.settings import Settings

        with TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.csv"
            settings = Settings(settings_path)
            details = settings.expose_schema()["data_collection_interval"]

            self.assertTrue(details.initial_only)
            self.assertEqual(settings.data_collection_interval.value, 0.1)

            settings.data_collection_interval.value = 0.75
            settings.write_csv()
            loaded_settings = Settings(settings_path)

            self.assertEqual(
                loaded_settings.data_collection_interval.value,
                0.75,
            )

    def test_compute_shader_uses_gray_scott_update(self):
        shader = ReactionDiffusionSimulation.COMPUTE_SHADER

        self.assertIn("current.r * current.g * current.g", shader)
        self.assertIn("u_feed_rate * (1.0 - current.r)", shader)
        self.assertIn("(u_kill_rate + u_feed_rate) * current.g", shader)
        self.assertIn("layout(rg32f", shader)

    def test_step_subdivides_scaled_dt_without_clamping_elapsed_time(self):
        simulation = object.__new__(ReactionDiffusionSimulation)
        simulation.grid_width = Setting(16)
        simulation.grid_height = Setting(16)
        simulation.schema = {
            "diffusion_a": SimpleNamespace(setting=Setting(1.0)),
            "diffusion_b": SimpleNamespace(setting=Setting(0.5)),
            "feed_rate": SimpleNamespace(setting=Setting(0.055)),
            "kill_rate": SimpleNamespace(setting=Setting(0.062)),
        }
        simulation._compute_program = FakeComputeProgram()
        simulation.grid_a = FakeTexture()
        simulation.grid_b = FakeTexture()
        simulation._current_grid = 0
        simulation.ctx = SimpleNamespace(memory_barrier=lambda: None)

        simulation.step(1.5 / 60)

        self.assertEqual(simulation._compute_program.time_steps, [0.75, 0.75])
        self.assertEqual(simulation._current_grid, 0)


if __name__ == "__main__":
    unittest.main()
