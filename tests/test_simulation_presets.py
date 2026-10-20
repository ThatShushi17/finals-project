import unittest

import numpy as np
import pandas as pd

from src.engine.simulation.three.n_parts.solar_system import (
    PLANETARY_DATA_PATH,
    solar_system_initial_conditions,
)
from src.settings import Setting
from src.simulations.ising import IsingSimulation
from src.simulations.fluid_dynamics import FluidDynamicsSimulation
from src.simulations.reaction_diffusion import ReactionDiffusionSimulation


class TestIsingPresets(unittest.TestCase):
    def test_discrete_preset_shape_compares_setting_values(self):
        simulation = object.__new__(IsingSimulation)
        simulation.grid_width = Setting(100)
        simulation.grid_height = Setting(100)

        grid = simulation._load_initial_grid("ordered_down")

        self.assertEqual(grid.shape, (100, 100))
        self.assertTrue(np.all(grid == 0))

    def test_bundled_presets_are_valid_binary_grids(self):
        preset_names = ("checkerboard", "ordered_down", "ordered_up", "stripes")
        schema = IsingSimulation.get_schema()

        self.assertEqual(
            schema["initial_grid"].options,
            ("random", *preset_names),
        )
        self.assertEqual(schema["initial_grid"].default_value, "random")
        for name in preset_names:
            with self.subTest(preset=name):
                grid = pd.read_csv(
                    IsingSimulation.PRESET_PATH / f"{name}.csv",
                    header=None,
                ).to_numpy()
                self.assertEqual(grid.shape, (100, 100))
                self.assertTrue(np.isin(grid, (0, 1)).all())

        checkerboard = pd.read_csv(
            IsingSimulation.PRESET_PATH / "checkerboard.csv",
            header=None,
        ).to_numpy()
        self.assertTrue(np.array_equal(checkerboard[1:, 1:], checkerboard[:-1, :-1]))
        self.assertNotEqual(checkerboard[0, 0], checkerboard[0, 1])
        self.assertTrue(
            np.all(
                pd.read_csv(
                    IsingSimulation.PRESET_PATH / "ordered_up.csv",
                    header=None,
                ).to_numpy()
                == 1
            )
        )
        self.assertTrue(
            np.all(
                pd.read_csv(
                    IsingSimulation.PRESET_PATH / "ordered_down.csv",
                    header=None,
                ).to_numpy()
                == 0
            )
        )


class TestReactionDiffusionCsvPresets(unittest.TestCase):
    def test_presets_are_discovered_from_csv_files(self):
        preset_files = sorted(
            ReactionDiffusionSimulation.PRESET_PATH.glob("*.csv")
        )
        schema = ReactionDiffusionSimulation.get_schema()

        self.assertEqual(
            schema["initial_pattern"].options,
            tuple(path.stem for path in preset_files),
        )
        self.assertEqual(
            set(schema["initial_pattern"].options),
            {"central_seed", "multiple_spots", "stripes", "rings"},
        )


class TestFluidDynamicsPresets(unittest.TestCase):
    def test_presets_configure_addable_flow_meshes(self):
        schema = FluidDynamicsSimulation.get_schema()
        preset = schema["preset"]
        meshes = schema["meshes"]

        self.assertEqual(
            preset.options,
            ("jet_channel", "vortex_forcefield"),
        )
        self.assertEqual(len(meshes.details), 2)
        self.assertEqual(
            set(meshes.details[0].details),
            {
                "shape",
                "center_x",
                "center_y",
                "width",
                "height",
            },
        )
        flow_source = schema["flow_source"]
        self.assertEqual(flow_source.opacity, 0.4)
        self.assertEqual(
            flow_source.details["source_type"].setting.value,
            "Inflow Jet",
        )
        preset.selection_callback("vortex_forcefield")
        self.assertEqual(len(meshes.details), 0)
        self.assertEqual(
            flow_source.details["source_type"].setting.value,
            "Force Field",
        )
        self.assertEqual(
            flow_source.details["fz"].setting.value,
            1.5,
        )
        self.assertEqual(
            meshes.generation_callback().name,
            "Mesh 1",
        )

    def test_obstacles_and_independent_fields_build_flow_textures(self):
        schema = FluidDynamicsSimulation.get_schema()
        simulation = object.__new__(FluidDynamicsSimulation)
        simulation.grid_width = 48
        simulation.grid_height = 32

        class TextureCapture:
            data: bytes | None = None

            def write(self, data: bytes, alignment: int = 1) -> None:
                self.data = data

        simulation._source_texture = TextureCapture()
        simulation._jet_mask_texture = TextureCapture()
        simulation._obstacle_texture = TextureCapture()
        simulation._dye_source_texture = TextureCapture()
        simulation.schema = schema
        simulation._rebuild_mesh_fields()

        jet_mask = np.frombuffer(
            simulation._jet_mask_texture.data,
            dtype=np.float32,
        ).reshape((32, 48))
        obstacle_mask = np.frombuffer(
            simulation._obstacle_texture.data,
            dtype=np.float32,
        ).reshape((32, 48))
        sources = np.frombuffer(
            simulation._source_texture.data,
            dtype=np.float32,
        ).reshape((32, 48, 4))
        dye_sources = np.frombuffer(
            simulation._dye_source_texture.data,
            dtype=np.float32,
        ).reshape((32, 48))
        self.assertGreater(float(jet_mask.sum()), 0.0)
        self.assertGreater(float(obstacle_mask.sum()), 0.0)
        self.assertGreater(float(np.abs(sources[..., 2:]).sum()), 0.0)
        self.assertTrue(np.all(sources[obstacle_mask > 0.5] == 0.0))
        self.assertTrue(np.all(jet_mask[obstacle_mask > 0.5] == 0.0))
        self.assertTrue(np.all(dye_sources[obstacle_mask > 0.5] == 0.0))

        schema["meshes"].details.clear()
        simulation._rebuild_mesh_fields()
        jet_only_solids = np.frombuffer(
            simulation._obstacle_texture.data,
            dtype=np.float32,
        ).reshape((32, 48))
        jet_only_mask = np.frombuffer(
            simulation._jet_mask_texture.data,
            dtype=np.float32,
        ).reshape((32, 48))
        self.assertGreater(float(jet_only_solids.sum()), 0.0)
        self.assertGreater(float(jet_only_mask.sum()), 0.0)
        self.assertTrue(np.all(jet_only_mask[jet_only_solids > 0.5] == 0.0))

        schema["flow_source"].details["source_type"].setting.value = "Off"
        simulation._rebuild_mesh_fields()
        self.assertEqual(
            float(np.frombuffer(
                simulation._jet_mask_texture.data,
                dtype=np.float32,
            ).sum()),
            0.0,
        )
        jet_solids = np.frombuffer(
            simulation._obstacle_texture.data,
            dtype=np.float32,
        ).reshape((32, 48))
        self.assertEqual(float(jet_solids.sum()), 0.0)

        schema["preset"].selection_callback("vortex_forcefield")
        simulation._rebuild_mesh_fields()
        sources = np.frombuffer(
            simulation._source_texture.data,
            dtype=np.float32,
        ).reshape((32, 48, 4))
        self.assertGreater(float(np.abs(sources[..., :2]).sum()), 0.0)
        self.assertEqual(
            schema["flow_source"].details["source_type"].setting.value,
            "Force Field",
        )
        self.assertEqual(
            float(np.frombuffer(
                simulation._jet_mask_texture.data,
                dtype=np.float32,
            ).sum()),
            0.0,
        )
        self.assertEqual(
            float(np.frombuffer(
                simulation._obstacle_texture.data,
                dtype=np.float32,
            ).sum()),
            0.0,
        )


class TestSolarSystemData(unittest.TestCase):
    def test_orbital_elements_are_loaded_from_misc_csv(self):
        self.assertTrue(PLANETARY_DATA_PATH.is_file())
        source = pd.read_csv(PLANETARY_DATA_PATH)
        initial_conditions = solar_system_initial_conditions()

        self.assertEqual(len(source), 9)
        self.assertEqual(len(initial_conditions), len(source))
        self.assertEqual(
            [state[0] for state in initial_conditions],
            source["name"].tolist(),
        )


if __name__ == "__main__":
    unittest.main()
