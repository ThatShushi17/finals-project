import unittest
from types import SimpleNamespace

import numpy as np
import pygame

from src.engine.ui.component import Component
from src.engine.ui.components.buttons import Button
from src.engine.ui.components.container import Container
from src.engine.ui.components.dropdown import Dropdown
from src.engine.ui.components.slider import Slider
from src.engine.simulation.three.n_parts.n_particle import NParticleSimulation
from src.engine.simulation.three.n_parts.solar_system import G_AU
from src.engine.simulation.three.n_parts.particle_groups import (
	create_particle_group_list,
)
from src.enums import Accents
from src.settings import CompoundDetails, InputDetails, ListDetails
from src.simulations.boids import BoidsSimulation
from src.simulations.gravity import GravitySimulation
from src.engine.ui.menu_system import MenuSystem
from src.enums import Position


class FakeColorScheme:
	def accent(self, accent: Accents) -> pygame.Color:
		colors = {
			Accents.BLUE: pygame.Color(0, 0, 255),
			Accents.GREEN: pygame.Color(0, 255, 0),
			Accents.ORANGE: pygame.Color(255, 128, 0),
			Accents.PINK: pygame.Color(255, 0, 255),
		}
		return colors[accent]

	def fg_bold(self):
		return pygame.Color(255, 255, 255)

	def fg(self):
		return pygame.Color(200, 200, 200)

	def bg_bold(self):
		return pygame.Color(20, 20, 20)

	def bg_border(self):
		return pygame.Color(0, 0, 0)

	def fg_hover(self):
		return pygame.Color(255, 255, 255)


class TestNParticleSimulation(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		pygame.font.init()

	def test_particle_group_list_generates_and_binds_compound_details(self):
		details = create_particle_group_list()

		self.assertIsInstance(details, ListDetails)
		self.assertEqual(len(details.details), 1)
		generated = details.generation_callback()
		details.details.append(generated)

		self.assertIsInstance(generated, CompoundDetails)
		self.assertEqual(generated.name, "Particle Group 2")
		self.assertEqual(len(details.details), 2)
		self.assertEqual(
			set(generated.details),
			{
				"count",
				"mass",
				"position_x",
				"position_y",
				"position_z",
				"velocity_x",
				"velocity_y",
				"velocity_z",
				"color",
			},
		)
		self.assertTrue(details.initial_only)
		self.assertTrue(generated.initial_only)
		self.assertTrue(
			all(setting.initial_only for setting in generated.details.values())
		)

	def test_list_details_has_a_default_detail_factory(self):
		details = ListDetails(name="Items", details=[])

		self.assertIsInstance(details.generation_callback(), InputDetails)
		self.assertEqual(details.opacity, 0.4)

	def test_dropdown_popup_draws_beyond_container_clip(self):
		root = Component((0, 0), (200, 200))
		container = Container(cross_length=200, cross_percent=0)
		root.add_child(container)
		container.rect = pygame.Rect(0, 0, 200, 50)
		dropdown = Dropdown(
			(0, 0),
			min_width=120,
			options=("Blue", "Green"),
			placeholder_text="Color",
			font=pygame.font.Font(None, 16),
			anchor=Position.TOP_LEFT,
			dock=Position.TOP_LEFT,
		)
		container.add_child(dropdown)
		dropdown.rect.topleft = (20, 20)
		dropdown.is_open = True
		surface = pygame.Surface((200, 200))
		surface.fill((1, 2, 3))

		container.draw(surface)

		popup_point = (
			dropdown.rect.left + 50,
			dropdown.rect.bottom + dropdown.option_height // 2,
		)
		self.assertGreater(popup_point[1], container.rect.bottom)
		self.assertEqual(surface.get_at(popup_point)[:3], (30, 30, 30))

	def test_list_settings_render_compounds_and_bind_generated_details(self):
		menu = object.__new__(MenuSystem)
		menu.color_scheme = FakeColorScheme()
		menu.font_handler = SimpleNamespace(
			get_font=lambda: pygame.font.Font(None, 16),
		)
		parent = Component((0, 0), (800, 1000))
		container = Container()
		parent.add_child(container)
		details = create_particle_group_list()

		menu.add_settings_from_schema(
			container,
			{"particle_groups": details},
		)

		list_container = container.children[0]
		self.assertIsInstance(list_container, Container)
		self.assertIsNone(list_container.background_color)
		self.assertEqual(len(details.details), 1)
		add_button = list_container.children[-1]
		self.assertIsInstance(add_button, Button)

		add_button.callback()

		self.assertEqual(len(details.details), 2)
		self.assertEqual(list_container.children[-1], add_button)
		self.assertEqual(
			sum(isinstance(child, Container) for child in list_container.children),
			2,
		)
		group_containers = [
			child
			for child in list_container.children
			if isinstance(child, Container)
		]
		self.assertEqual(len(group_containers), 2)
		self.assertEqual(
			group_containers[0].rect.height,
			group_containers[0]._content_length()
			+ 2 * group_containers[0].SCROLL_PADDING,
		)
		self.assertEqual(
			group_containers[0].background_color(),
			pygame.Color(0, 0, 255, 102),
		)
		details.details[0].details["color"].setting.value = "orange"  # type: ignore[union-attr]
		self.assertEqual(
			group_containers[0].background_color(),
			pygame.Color(255, 128, 0, 102),
		)

	def test_particle_state_combines_particle_groups_and_group_properties(self):
		schema = GravitySimulation.get_schema()
		group_list = schema["particle_groups"]
		first_group = group_list.details[0]  # type: ignore[union-attr]
		group_list.details[:] = [first_group]  # type: ignore[union-attr]
		first_group.details["count"].setting.value = 3  # type: ignore[union-attr]
		first_group.details["mass"].setting.value = 2.0  # type: ignore[union-attr]
		second_group = group_list.generation_callback()  # type: ignore[union-attr]
		second_group.details["count"].setting.value = 2  # type: ignore[union-attr]
		second_group.details["mass"].setting.value = 4.0  # type: ignore[union-attr]
		group_list.details.append(second_group)  # type: ignore[union-attr]

		positions, velocities, masses, colors = NParticleSimulation._build_particle_state(
			schema,
			FakeColorScheme(),  # type: ignore[arg-type]
		)

		self.assertEqual(positions.shape, (5, 3))
		self.assertEqual(velocities.shape, (5, 3))
		self.assertEqual(colors.shape, (5, 3))
		np.testing.assert_array_equal(masses, [2.0, 2.0, 2.0, 4.0, 4.0])

	def test_gravity_accelerations_are_pairwise_and_mass_weighted(self):
		positions = np.array([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
		masses = np.array([2.0, 4.0])

		acceleration = GravitySimulation._calculate_accelerations(
			positions,
			masses,
			gravitational_constant=1.0,
			softening=0.0,
		)

		self.assertGreater(acceleration[0, 0], 0.0)
		self.assertLess(acceleration[1, 0], 0.0)
		self.assertAlmostEqual(
			masses[0] * acceleration[0, 0],
			-masses[1] * acceleration[1, 0],
		)
		self.assertTrue(np.isfinite(acceleration).all())

	def test_boids_accelerations_are_finite_and_report_neighbor_counts(self):
		positions = np.array([
			[0.0, 0.0, 0.0],
			[0.2, 0.0, 0.0],
			[0.0, 0.3, 0.0],
			[2.0, 2.0, 2.0],
		])
		velocities = np.array([
			[0.1, 0.0, 0.0],
			[0.0, 0.1, 0.0],
			[0.0, 0.0, 0.1],
			[0.0, 0.0, 0.0],
		])

		acceleration, neighbors = BoidsSimulation._calculate_accelerations(
			positions,
			velocities,
			perception_radius=0.5,
			separation_weight=1.0,
			alignment_weight=1.0,
			cohesion_weight=1.0,
			max_acceleration=2.0,
		)

		np.testing.assert_array_equal(neighbors, [2, 2, 2, 0])
		self.assertTrue(np.isfinite(acceleration).all())
		self.assertGreater(acceleration[3, 0], 0.0)

	def test_boid_wings_are_flat_and_follow_three_dimensional_heading(self):
		positions = np.array([
			[0.0, 0.0, 0.0],
			[1.0, 1.0, 1.0],
		])
		velocities = np.array([
			[0.0, 0.0, 2.0],
			[0.0, 3.0, 0.0],
		])

		triangles = BoidsSimulation._make_wing_vertices(
			positions,
			velocities,
			BoidsSimulation.WING_LENGTH,
		)

		self.assertEqual(triangles.shape, (2, 3, 3))
		self.assertTrue(np.isfinite(triangles).all())
		for triangle in triangles:
			normal = np.cross(
				triangle[1] - triangle[0],
				triangle[2] - triangle[0],
			)
			self.assertGreater(np.linalg.norm(normal), 0.0)
		np.testing.assert_allclose(
			triangles[0, 0] - positions[0],
			[0.0, 0.0, BoidsSimulation.WING_LENGTH],
		)

	def test_solar_system_groups_receive_distinct_procedural_surface_ids(self):
		schema = GravitySimulation.get_schema()

		surface_ids = NParticleSimulation._build_surface_ids(schema)

		np.testing.assert_array_equal(
			surface_ids,
			np.arange(1.0, 10.0, dtype=np.float32),
		)

	def test_particle_group_settings_are_excluded_from_live_controls(self):
		for simulation_class in (GravitySimulation, BoidsSimulation):
			schema = simulation_class.get_schema()
			self.assertTrue(schema["particle_groups"].initial_only)
			self.assertFalse(schema["simulation_speed"].initial_only)
			live_control = (
				"gravitational_constant"
				if simulation_class is GravitySimulation
				else "perception_radius"
			)
			self.assertFalse(schema[live_control].initial_only)

	def test_gravity_preset_loads_stable_solar_system_initial_conditions(self):
		schema = GravitySimulation.get_schema()
		preset = schema["preset"]
		groups = schema["particle_groups"]
		self.assertEqual(preset.default_value, "Solar System")  # type: ignore[union-attr]
		self.assertEqual(
			schema["gravitational_constant"].setting.value,  # type: ignore[union-attr]
			G_AU,
		)

		positions, velocities, masses, _ = NParticleSimulation._build_particle_state(
			schema,
			FakeColorScheme(),  # type: ignore[arg-type]
		)
		self.assertEqual(len(groups.details), 9)  # type: ignore[union-attr]
		self.assertEqual(positions.shape, (9, 3))
		np.testing.assert_allclose(
			np.sum(masses[:, None] * velocities, axis=0),
			np.zeros(3),
			atol=1e-12,
		)

		earth_index = 3
		sun_index = 0
		initial_earth_radius = np.linalg.norm(
			positions[earth_index] - positions[sun_index]
		)
		softening = float(schema["softening"].setting.value)  # type: ignore[union-attr]
		for _ in range(1200):
			acceleration = GravitySimulation._calculate_accelerations(
				positions,
				masses,
				G_AU,
				softening,
			)
			step = 1.0 / 1200.0
			positions += velocities * step + 0.5 * acceleration * step**2
			next_acceleration = GravitySimulation._calculate_accelerations(
				positions,
				masses,
				G_AU,
				softening,
			)
			velocities += 0.5 * (acceleration + next_acceleration) * step

		final_earth_radius = np.linalg.norm(
			positions[earth_index] - positions[sun_index]
		)
		self.assertLess(abs(final_earth_radius - initial_earth_radius), 0.01)

		preset.selection_callback("Scattered Cloud")  # type: ignore[union-attr]
		self.assertEqual(
			schema["gravitational_constant"].setting.value,  # type: ignore[union-attr]
			0.15,
		)
		self.assertEqual(groups.details[0].details["count"].setting.value, 16)  # type: ignore[union-attr]
		preset.selection_callback("Solar System")  # type: ignore[union-attr]
		self.assertEqual(groups.details[0].details["count"].setting.value, 1)  # type: ignore[union-attr]

	def test_gravity_preset_updates_visible_controls(self):
		menu = object.__new__(MenuSystem)
		menu.color_scheme = FakeColorScheme()
		menu.font_handler = SimpleNamespace(
			get_font=lambda: pygame.font.Font(None, 16),
		)
		root = Component((0, 0), (800, 2400))
		container = Container()
		root.add_child(container)
		schema = GravitySimulation.get_schema()
		menu.add_settings_from_schema(container, schema)

		def descendants(component):
			for child in component.children:
				yield child
				yield from descendants(child)

		components = list(descendants(container))
		preset_dropdown = next(
			component
			for component in components
			if isinstance(component, Dropdown)
			and getattr(component, "_setting_details", None) is schema["preset"]
		)
		gravitational_slider = next(
			component
			for component in components
			if isinstance(component, Slider)
			and getattr(component, "_setting_details", None)
			is schema["gravitational_constant"]
		)

		preset_dropdown.on_change("Scattered Cloud")

		self.assertEqual(
			schema["gravitational_constant"].setting.value,  # type: ignore[union-attr]
			0.15,
		)
		self.assertEqual(gravitational_slider.value, 0.15)


if __name__ == "__main__":
	unittest.main()
