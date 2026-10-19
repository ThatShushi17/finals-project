import moderngl
import numpy as np
from pathlib import Path
from numpy.typing import NDArray

from src.engine.simulation.three.n_parts.n_particle import NParticleSimulation
from src.engine.simulation.three.n_parts.particle_groups import (
	create_particle_group_list,
)
from src.engine.simulation.three.n_parts.solar_system import (
	G_AU,
	apply_scattered_cloud,
	apply_solar_system,
)
from src.engine.ui.color_scheme import ColorScheme
from src.settings import PresetDetails, Setting, SliderDetails
from src.types import SettingsSchema


def _set_uniform(
	program: moderngl.ComputeShader,
	name: str,
	value: object,
) -> None:
	program[name].value = value  # type: ignore


class GravitySimulation(NParticleSimulation):
	METRIC_PLOT_TITLE = "N-body gravitational energy"
	WORLD_BOUNDS = ((-35.0, -35.0, -35.0), (35.0, 35.0, 35.0))
	MAX_INTEGRATION_STEP = 1.0 / 1200.0
	WORKGROUP_SIZE = 128
	ACCELERATION_SHADER = (
		Path(__file__).resolve().parents[1]
		/ "shaders"
		/ "simulation"
		/ "compute"
		/ "gravity_acceleration.comp"
	).read_text(encoding="utf-8")
	INTEGRATION_SHADER = (
		Path(__file__).resolve().parents[1]
		/ "shaders"
		/ "simulation"
		/ "compute"
		/ "gravity_integrate.comp"
	).read_text(encoding="utf-8")

	@classmethod
	def get_schema(cls) -> SettingsSchema:
		schema = super().get_schema()
		groups = create_particle_group_list(initial_groups=9)
		gravitational_constant = Setting(G_AU)
		softening = Setting(0.001)
		apply_solar_system(groups)

		def apply_preset(name: str) -> None:
			if name == "Solar System":
				gravitational_constant.value = G_AU
				softening.value = 0.001
				apply_solar_system(groups)
			elif name == "Scattered Cloud":
				gravitational_constant.value = 0.15
				softening.value = 0.08
				apply_scattered_cloud(groups)
			else:
				raise ValueError(f"Unknown gravity preset: {name!r}")

		schema.update({
			"preset": PresetDetails(
				"Preset",
				setting=Setting("Solar System"),
				options=("Solar System", "Scattered Cloud"),
				placeholder_text="Choose a preset",
				default_value="Solar System",
				initial_only=True,
				selection_callback=apply_preset,
			),
			"particle_groups": groups,
			"gravitational_constant": SliderDetails(
				"Gravitational Constant",
				setting=gravitational_constant,
				lower_bound=0.0,
				upper_bound=100.0,
			),
			"softening": SliderDetails(
				"Distance Softening",
				setting=softening,
				lower_bound=0.0001,
				upper_bound=0.5,
			),
		})
		return schema

	def __init__(
		self,
		ctx: moderngl.Context,
		schema: SettingsSchema,
		color_scheme: ColorScheme,
	):
		super().__init__(ctx=ctx, schema=schema, color_scheme=color_scheme)
		self.camera_distance = 55.0
		self._gravity_acceleration_program = ctx.compute_shader(
			self.ACCELERATION_SHADER
		)
		self._gravity_integration_program = ctx.compute_shader(
			self.INTEGRATION_SHADER
		)
		self._gravity_positions = ctx.buffer(
			self._vec4_bytes(self.positions)
		)
		self._gravity_velocities = ctx.buffer(
			self._vec4_bytes(self.velocities)
		)
		self._gravity_masses = ctx.buffer(
			self._vec4_bytes(self.masses[:, None])
		)
		self._gravity_acceleration_a = ctx.buffer(
			reserve=self.particle_count * 16
		)
		self._gravity_acceleration_b = ctx.buffer(
			reserve=self.particle_count * 16
		)
		self._gravity_group_count = (
			self.particle_count + self.WORKGROUP_SIZE - 1
		) // self.WORKGROUP_SIZE

	@staticmethod
	def _vec4_bytes(values: NDArray[np.float64]) -> bytes:
		contiguous = np.asarray(values, dtype=np.float32)
		if contiguous.ndim == 1:
			contiguous = contiguous[:, None]
		vec4 = np.zeros((len(contiguous), 4), dtype=np.float32)
		vec4[:, :contiguous.shape[1]] = contiguous
		return vec4.tobytes(order="C")

	def apply_law(self, dt: float) -> None:
		substep_count = max(
			1,
			int(np.ceil(dt / self.MAX_INTEGRATION_STEP)),
		)
		substep = dt / substep_count
		gravitational_constant_details = self.schema["gravitational_constant"]
		softening_details = self.schema["softening"]
		if not isinstance(gravitational_constant_details, SliderDetails):
			raise TypeError("Gravitational constant must be a slider setting.")
		if not isinstance(softening_details, SliderDetails):
			raise TypeError("Gravity softening must be a slider setting.")
		gravitational_constant = float(gravitational_constant_details.setting.value)
		softening = float(softening_details.setting.value)

		self._bind_acceleration_buffers(self._gravity_acceleration_a)
		_set_uniform(
			self._gravity_acceleration_program,
			"u_count",
			self.particle_count,
		)
		_set_uniform(
			self._gravity_acceleration_program,
			"u_gravitational_constant",
			gravitational_constant,
		)
		_set_uniform(
			self._gravity_acceleration_program,
			"u_softening",
			softening,
		)
		self._gravity_acceleration_program.run(
			group_x=self._gravity_group_count,
			group_y=1,
			group_z=1,
		)
		self.ctx.memory_barrier()

		acceleration_current = self._gravity_acceleration_a
		acceleration_next = self._gravity_acceleration_b
		for _ in range(substep_count):
			self._bind_integration_buffers(
				acceleration_current,
				acceleration_next,
			)
			_set_uniform(self._gravity_integration_program, "u_stage", 0)
			_set_uniform(
				self._gravity_integration_program,
				"u_time_step",
				substep,
			)
			self._gravity_integration_program.run(
				group_x=self._gravity_group_count,
				group_y=1,
				group_z=1,
			)
			self.ctx.memory_barrier()

			self._bind_acceleration_buffers(acceleration_next)
			self._gravity_acceleration_program.run(
				group_x=self._gravity_group_count,
				group_y=1,
				group_z=1,
			)
			self.ctx.memory_barrier()

			self._bind_integration_buffers(
				acceleration_current,
				acceleration_next,
			)
			_set_uniform(self._gravity_integration_program, "u_stage", 1)
			self._gravity_integration_program.run(
				group_x=self._gravity_group_count,
				group_y=1,
				group_z=1,
			)
			self.ctx.memory_barrier()
			acceleration_current, acceleration_next = (
				acceleration_next,
				acceleration_current,
			)

		position_values = np.frombuffer(
			self._gravity_positions.read(),
			dtype=np.float32,
		).reshape((-1, 4))
		velocity_values = np.frombuffer(
			self._gravity_velocities.read(),
			dtype=np.float32,
		).reshape((-1, 4))
		self.positions[:] = position_values[:, :3]
		self.velocities[:] = velocity_values[:, :3]

	def _bind_acceleration_buffers(
		self,
		output_accelerations: moderngl.Buffer,
	) -> None:
		self._gravity_positions.bind_to_storage_buffer(0)
		self._gravity_masses.bind_to_storage_buffer(1)
		output_accelerations.bind_to_storage_buffer(2)

	def _bind_integration_buffers(
		self,
		previous_accelerations: moderngl.Buffer,
		next_accelerations: moderngl.Buffer,
	) -> None:
		self._gravity_positions.bind_to_storage_buffer(0)
		self._gravity_velocities.bind_to_storage_buffer(1)
		previous_accelerations.bind_to_storage_buffer(2)
		next_accelerations.bind_to_storage_buffer(3)
		_set_uniform(
			self._gravity_integration_program,
			"u_count",
			self.particle_count,
		)

	def cleanup(self) -> None:
		for resource in (
			self._gravity_positions,
			self._gravity_velocities,
			self._gravity_masses,
			self._gravity_acceleration_a,
			self._gravity_acceleration_b,
			self._gravity_acceleration_program,
			self._gravity_integration_program,
		):
			resource.release()
		super().cleanup()

	@staticmethod
	def _calculate_accelerations(
		positions: NDArray[np.float64],
		masses: NDArray[np.float64],
		gravitational_constant: float,
		softening: float,
	) -> NDArray[np.float64]:
		displacements: NDArray[np.float64] = (
			positions[None, :, :] - positions[:, None, :]
		)
		distance_squared: NDArray[np.float64] = (
			np.sum(displacements * displacements, axis=2) + softening**2
		)
		np.fill_diagonal(distance_squared, np.inf)
		inverse_distance_cubed: NDArray[np.float64] = np.power(
			distance_squared,
			-1.5,
		)
		accelerations: NDArray[np.float64] = gravitational_constant * np.sum(
			displacements
			* inverse_distance_cubed[:, :, None]
			* masses[None, :, None],
			axis=1,
		)
		return accelerations

	def get_metrics(self) -> dict[str, float]:
		kinetic_energy = 0.5 * float(
			np.sum(
				self.masses
				* np.sum(self.velocities * self.velocities, axis=1)
			)
		)
		displacements = self.positions[None, :, :] - self.positions[:, None, :]
		distances = np.sqrt(
			np.sum(displacements * displacements, axis=2)
			+ float(self.schema["softening"].setting.value) ** 2  # type: ignore
		)
		inverse_distances = np.divide(
			1.0,
			distances,
			out=np.zeros_like(distances),
			where=distances > 0,
		)
		np.fill_diagonal(inverse_distances, 0.0)
		potential_energy = -0.5 * float(
			self.schema["gravitational_constant"].setting.value  # type: ignore
		) * float(
			np.sum(
				self.masses[:, None]
				* self.masses[None, :]
				* inverse_distances
			)
		)
		return {
			"Kinetic Energy": kinetic_energy,
			"Potential Energy": potential_energy,
			"Total Energy": kinetic_energy + potential_energy,
		}
