import moderngl
import numpy as np

from src.engine.simulation.three.n_parts.n_particle import NParticleSimulation
from src.engine.simulation.three.n_parts.particle_groups import (
	create_particle_group_list,
)
from src.engine.ui.color_scheme import ColorScheme
from src.settings import Setting, SliderDetails
from src.types import SettingsSchema


class BoidsSimulation(NParticleSimulation):
	METRIC_PLOT_TITLE = "Boids flock speed and neighbor count"
	WORLD_HALF_SIZE = 2.0
	WORLD_BOUNDS = (
		(-WORLD_HALF_SIZE, -WORLD_HALF_SIZE, -WORLD_HALF_SIZE),
		(WORLD_HALF_SIZE, WORLD_HALF_SIZE, WORLD_HALF_SIZE),
	)
	WING_LENGTH = 0.11
	POINT_VERTEX_COUNT = 3
	PARTICLE_MODE = moderngl.TRIANGLES
	PARTICLE_FORMAT = "3f 3f 3f"
	PARTICLE_ATTRIBUTES = (
		"in_position",
		"in_color",
		"in_barycentric",
	)

	VERTEX_SHADER = """
	#version 330
	in vec3 in_position;
	in vec3 in_color;
	in vec3 in_barycentric;
	uniform mat4 u_view_projection;
	out vec3 particle_color;
	out vec3 barycentric;

	void main() {
		gl_Position = u_view_projection * vec4(in_position, 1.0);
		particle_color = in_color;
		barycentric = in_barycentric;
	}
	"""

	FRAGMENT_SHADER = """
	#version 330
	in vec3 particle_color;
	in vec3 barycentric;
	out vec4 frag_color;

	void main() {
		float edge_distance = min(
			barycentric.x,
			min(barycentric.y, barycentric.z)
		);
		float edge_width = max(fwidth(edge_distance) * 2.0, 0.004);
		float interior = smoothstep(0.0, edge_width * 2.5, edge_distance);
		vec3 edge_color = particle_color * 0.28;
		frag_color = vec4(
			mix(edge_color, particle_color, interior),
			1.0
		);
	}
	"""

	@classmethod
	def get_schema(cls) -> SettingsSchema:
		schema = super().get_schema()
		schema.update({
			"particle_groups": create_particle_group_list(),
			"perception_radius": SliderDetails(
				"Perception Radius",
				setting=Setting(0.65),
				lower_bound=0.1,
				upper_bound=2.0,
			),
			"separation_weight": SliderDetails(
				"Separation Weight",
				setting=Setting(1.5),
				lower_bound=0.0,
				upper_bound=4.0,
			),
			"alignment_weight": SliderDetails(
				"Alignment Weight",
				setting=Setting(0.8),
				lower_bound=0.0,
				upper_bound=4.0,
			),
			"cohesion_weight": SliderDetails(
				"Cohesion Weight",
				setting=Setting(0.7),
				lower_bound=0.0,
				upper_bound=4.0,
			),
			"max_speed": SliderDetails(
				"Maximum Speed",
				setting=Setting(1.0),
				lower_bound=0.1,
				upper_bound=3.0,
			),
			"max_acceleration": SliderDetails(
				"Maximum Acceleration",
				setting=Setting(1.5),
				lower_bound=0.1,
				upper_bound=5.0,
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
		self._neighbor_counts = np.zeros(self.particle_count, dtype=np.int64)

	def apply_law(self, dt: float) -> None:
		acceleration, neighbor_counts = self._calculate_accelerations(
			self.positions,
			self.velocities,
			float(self.schema["perception_radius"].setting.value),  # type: ignore
			float(self.schema["separation_weight"].setting.value),  # type: ignore
			float(self.schema["alignment_weight"].setting.value),  # type: ignore
			float(self.schema["cohesion_weight"].setting.value),  # type: ignore
			float(self.schema["max_acceleration"].setting.value),  # type: ignore
		)
		self._neighbor_counts = neighbor_counts
		self.velocities += acceleration * dt
		speed = np.linalg.norm(self.velocities, axis=1)
		max_speed = float(self.schema["max_speed"].setting.value)  # type: ignore
		too_fast = speed > max_speed
		self.velocities[too_fast] *= (max_speed / speed[too_fast])[:, None]
		self.positions += self.velocities * dt
		self.positions[:] = (
			(self.positions + self.WORLD_HALF_SIZE)
			% (2.0 * self.WORLD_HALF_SIZE)
		) - self.WORLD_HALF_SIZE

	@staticmethod
	def _make_wing_vertices(
		positions: np.ndarray,
		velocities: np.ndarray,
		wing_length: float,
	) -> np.ndarray:
		speeds = np.linalg.norm(velocities, axis=1)
		headings = np.zeros_like(velocities)
		moving = speeds > 1e-8
		headings[moving] = velocities[moving] / speeds[moving, None]
		headings[~moving, 0] = 1.0

		world_up = np.broadcast_to(
			np.array([0.0, 1.0, 0.0]),
			headings.shape,
		)
		side = np.cross(headings, world_up)
		side_length = np.linalg.norm(side, axis=1)
		vertical_heading = side_length < 1e-8
		if np.any(vertical_heading):
			side[vertical_heading] = np.cross(
				headings[vertical_heading],
				np.array([1.0, 0.0, 0.0]),
			)
		side /= np.linalg.norm(side, axis=1)[:, None]

		return np.stack(
			(
				positions + headings * wing_length,
				positions - headings * wing_length * 0.5
					+ side * wing_length * 0.5,
				positions - headings * wing_length * 0.5
					- side * wing_length * 0.5,
			),
			axis=1,
		)

	def _vertex_data(self) -> bytes:
		triangles = self._make_wing_vertices(
			self.positions,
			self.velocities,
			self.WING_LENGTH,
		)
		colors = np.broadcast_to(
			self.particle_colors[:, None, :],
			(self.particle_count, 3, 3),
		)
		barycentric = np.broadcast_to(
			np.eye(3, dtype=np.float32)[None, :, :],
			(self.particle_count, 3, 3),
		)
		return np.concatenate(
			(
				triangles.astype(np.float32),
				colors,
				barycentric,
			),
			axis=2,
		).tobytes(order="C")

	@staticmethod
	def _calculate_accelerations(
		positions: np.ndarray,
		velocities: np.ndarray,
		perception_radius: float,
		separation_weight: float,
		alignment_weight: float,
		cohesion_weight: float,
		max_acceleration: float,
	) -> tuple[np.ndarray, np.ndarray]:
		displacements = positions[None, :, :] - positions[:, None, :]
		distances = np.linalg.norm(displacements, axis=2)
		neighbors = (distances > 0.0) & (distances < perception_radius)
		neighbor_counts = neighbors.sum(axis=1)
		counts = np.maximum(neighbor_counts, 1)[:, None]

		mean_positions = np.sum(
			np.where(neighbors[:, :, None], positions[None, :, :], 0.0),
			axis=1,
		) / counts
		mean_velocities = np.sum(
			np.where(neighbors[:, :, None], velocities[None, :, :], 0.0),
			axis=1,
		) / counts
		cohesion = mean_positions - positions
		alignment = mean_velocities - velocities

		separation_vectors = -displacements / np.maximum(
			distances[:, :, None],
			1e-6,
		) ** 2
		separation = np.sum(
			np.where(neighbors[:, :, None], separation_vectors, 0.0),
			axis=1,
		) / counts

		acceleration = (
			separation * separation_weight
			+ alignment * alignment_weight
			+ cohesion * cohesion_weight
		)
		acceleration_magnitude = np.linalg.norm(acceleration, axis=1)
		too_strong = acceleration_magnitude > max_acceleration
		acceleration[too_strong] *= (
			max_acceleration / acceleration_magnitude[too_strong]
		)[:, None]

		# Give isolated birds a deterministic heading so they rejoin the flock.
		isolated = neighbor_counts == 0
		if np.any(isolated):
			acceleration[isolated, 0] = max_acceleration
		return acceleration, neighbor_counts

	def get_metrics(self) -> dict[str, float]:
		return {
			"Mean Speed": float(np.mean(np.linalg.norm(self.velocities, axis=1))),
			"Mean Neighbors": float(np.mean(self._neighbor_counts)),
		}
