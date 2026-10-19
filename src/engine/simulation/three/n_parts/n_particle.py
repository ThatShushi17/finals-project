import struct

import moderngl
import numpy as np
import glm
from numpy.typing import NDArray

from .....settings import CompoundDetails, ListDetails, SettingDetails
from .....types import SettingsSchema
from ....ui.color_scheme import ColorScheme
from ..simulation_3d import Simulation3D
from .particle_groups import ACCENT_OPTIONS, setting_value


class NParticleSimulation(Simulation3D):
	positions: NDArray[np.float64]
	velocities: NDArray[np.float64]
	masses: NDArray[np.float64]
	particle_colors: NDArray[np.float32]
	particle_surface_ids: NDArray[np.float32]
	particle_count: int
	_particle_program: moderngl.Program
	_particle_buffer: moderngl.Buffer
	_particle_vao: moderngl.VertexArray
	POINT_VERTEX_COUNT = 1
	PARTICLE_MODE = moderngl.POINTS
	PARTICLE_FORMAT = "3f 3f 1f"
	PARTICLE_ATTRIBUTES = (
		"in_position",
		"in_color",
		"in_surface_id",
	)

	VERTEX_SHADER = """
	#version 330
	in vec3 in_position;
	in vec3 in_color;
	in float in_surface_id;
	uniform mat4 u_view_projection;
	out vec3 particle_color;
	flat out float surface_id;

	void main() {
		gl_Position = u_view_projection * vec4(in_position, 1.0);
		gl_PointSize = clamp(18.0 / gl_Position.w, 8.0, 24.0);
		particle_color = in_color;
		surface_id = in_surface_id;
	}
	"""

	FRAGMENT_SHADER = """
	#version 330
	in vec3 particle_color;
	flat in float surface_id;
	out vec4 frag_color;

	float hash21(vec2 p) {
		p = fract(p * vec2(123.34, 456.21));
		p += dot(p, p + 45.32);
		return fract(p.x * p.y);
	}

	void main() {
		vec2 coord = floor(gl_PointCoord * 32.0) / 32.0;
		vec2 point = (coord - 0.5) * 2.0;
		float radius = length(point);
		bool saturn = surface_id > 6.5 && surface_id < 7.5;
		float body_radius = saturn ? 0.48 : 0.82;
		float ring_radius = length(vec2(point.x, point.y * 3.0));
		bool ring = saturn && abs(point.y) < 0.34
			&& ring_radius > 0.56 && ring_radius < 1.02;

		if (!ring && radius > body_radius + 0.055) {
			discard;
		}

		if (ring && (radius > body_radius || abs(point.y) > 0.21)) {
			float band = 0.5 + 0.5 * sin(ring_radius * 74.0);
			vec3 ring_color = mix(
				vec3(0.42, 0.31, 0.18),
				vec3(0.91, 0.76, 0.52),
				band
			);
			frag_color = vec4(ring_color, 1.0);
			return;
		}

		vec3 normal = vec3(point / body_radius, 0.0);
		normal.z = sqrt(max(0.0, 1.0 - dot(normal.xy, normal.xy)));
		vec2 surface = floor((point / body_radius * 0.5 + 0.5) * 32.0);
		float variation = hash21(surface + surface_id * 17.0);
		float latitude = point.y / body_radius;
		float bands = 0.5 + 0.5 * sin(
			(latitude + 0.08 * sin(point.x * 11.0)) * 22.0
		);
		vec3 base_color = particle_color;

		if (surface_id > 0.5 && surface_id < 1.5) {
			base_color = mix(
				vec3(0.95, 0.24, 0.035),
				vec3(1.0, 0.82, 0.24),
				bands
			);
		} else if (surface_id > 1.5 && surface_id < 2.5) {
			base_color *= mix(0.48, 1.08, variation);
		} else if (surface_id > 2.5 && surface_id < 3.5) {
			base_color = mix(base_color * 0.68, vec3(0.92, 0.75, 0.43), bands);
		} else if (surface_id > 3.5 && surface_id < 4.5) {
			float continent = smoothstep(
				0.48, 0.62,
				sin(point.x * 8.0 + sin(point.y * 5.0))
					* cos(point.y * 7.0 - point.x * 3.0)
			);
			base_color = mix(
				vec3(0.08, 0.34, 0.82),
				vec3(0.12, 0.58, 0.26),
				continent
			);
		} else if (surface_id > 4.5 && surface_id < 5.5) {
			base_color = mix(base_color * 0.58, vec3(1.0, 0.50, 0.24), variation);
		} else if (surface_id > 5.5 && surface_id < 9.5) {
			base_color = mix(base_color * 0.72, base_color * 1.24, bands);
		}

		float lighting = 0.28 + 0.72 * max(
			dot(normalize(normal), normalize(vec3(-0.38, 0.52, 0.76))),
			0.0
		);
		float limb = 1.0 - smoothstep(
			body_radius - 0.06,
			body_radius + 0.025,
			radius
		);
		float outline = 1.0 - smoothstep(
			body_radius - 0.12,
			body_radius - 0.025,
			radius
		);
		vec3 shaded = base_color * lighting;
		shaded = mix(shaded, shaded * 0.28, outline * 0.68);
		if (surface_id > 0.5 && surface_id < 1.5) {
			shaded += vec3(0.30, 0.10, 0.015) * (1.0 - radius / body_radius);
		}
		if (limb <= 0.0) {
			discard;
		}
		frag_color = vec4(shaded, 1.0);
	}
	"""

	RANDOM_SEED = 23
	CLUSTER_RADIUS = 0.15
	SURFACE_IDS = {
		"Sun": 1.0,
		"Mercury": 2.0,
		"Venus": 3.0,
		"Earth": 4.0,
		"Mars": 5.0,
		"Jupiter": 6.0,
		"Saturn": 7.0,
		"Uranus": 8.0,
		"Neptune": 9.0,
	}

	def __init__(
		self,
		ctx: moderngl.Context,
		schema: SettingsSchema,
		color_scheme: ColorScheme,
	):
		super().__init__(ctx=ctx, schema=schema, color_scheme=color_scheme)
		self.positions, self.velocities, self.masses, self.particle_colors = (
			self._build_particle_state(schema, color_scheme)
		)
		self.particle_count = len(self.positions)
		self.particle_surface_ids = self._build_surface_ids(schema)

		self._particle_program = ctx.program(
			vertex_shader=self.VERTEX_SHADER,
			fragment_shader=self.FRAGMENT_SHADER,
		)
		self._particle_buffer = ctx.buffer(
			self._vertex_data(),
			dynamic=True,
		)
		self._particle_vao = ctx.vertex_array(  # type: ignore[reportUnknownMemberType]
			self._particle_program,
			[(
				self._particle_buffer,
				self.PARTICLE_FORMAT,
				*self.PARTICLE_ATTRIBUTES,
			)],
		)

	@classmethod
	def _build_particle_state(
		cls,
		schema: SettingsSchema,
		color_scheme: ColorScheme,
	) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
		groups_details = schema.get("particle_groups")
		if not isinstance(groups_details, ListDetails):
			raise ValueError("N-particle simulations require a particle_groups list.")

		rng = np.random.default_rng(cls.RANDOM_SEED)
		positions: list[np.ndarray] = []
		velocities: list[np.ndarray] = []
		masses: list[np.ndarray] = []
		colors: list[np.ndarray] = []
		for group in groups_details.details:
			if not isinstance(group, CompoundDetails):
				raise TypeError("Every particle group must be CompoundDetails.")
			group_settings = group.details
			count = int(cls._number_setting(group_settings, "count"))
			mass = float(cls._number_setting(group_settings, "mass"))
			center = np.array(
				[
					cls._number_setting(group_settings, "position_x"),
					cls._number_setting(group_settings, "position_y"),
					cls._number_setting(group_settings, "position_z"),
				],
				dtype=np.float64,
			)
			initial_velocity = np.array(
				[
					cls._number_setting(group_settings, "velocity_x"),
					cls._number_setting(group_settings, "velocity_y"),
					cls._number_setting(group_settings, "velocity_z"),
				],
				dtype=np.float64,
			)
			color_name = str(setting_value(group_settings["color"]))
			if color_name not in ACCENT_OPTIONS:
				raise ValueError(f"Unknown particle color: {color_name!r}")

			group_positions = np.repeat(center[None, :], count, axis=0)
			if count > 1:
				group_positions += rng.normal(
					0.0,
					cls.CLUSTER_RADIUS,
					size=(count, 3),
				)
			group_velocities = np.repeat(
				initial_velocity[None, :],
				count,
				axis=0,
			)
			if count > 1:
				group_velocities += rng.normal(0.0, 0.02, size=(count, 3))

			pygame_color = color_scheme.accent(ACCENT_OPTIONS[color_name])
			color = np.array(
				[
					pygame_color.r / 255.0,
					pygame_color.g / 255.0,
					pygame_color.b / 255.0,
				],
				dtype=np.float32,
			)
			positions.append(group_positions)
			velocities.append(group_velocities)
			masses.append(np.full(count, mass, dtype=np.float64))
			colors.append(np.repeat(color[None, :], count, axis=0))

		if not positions:
			raise ValueError("At least one particle group is required.")
		return (
			np.concatenate(positions),
			np.concatenate(velocities),
			np.concatenate(masses),
			np.concatenate(colors),
		)

	@classmethod
	def _build_surface_ids(cls, schema: SettingsSchema) -> np.ndarray:
		groups = schema["particle_groups"]
		if not isinstance(groups, ListDetails):
			raise ValueError("N-particle simulations require a particle_groups list.")
		surface_ids: list[float] = []
		for group in groups.details:
			if not isinstance(group, CompoundDetails):
				raise TypeError("Every particle group must be CompoundDetails.")
			count = int(cls._number_setting(group.details, "count"))
			surface_id = cls.SURFACE_IDS.get(group.name, 0.0)
			surface_ids.extend([surface_id] * count)
		return np.asarray(surface_ids, dtype=np.float32)

	@staticmethod
	def _number_setting(
		details: dict[str, SettingDetails],
		name: str,
	) -> float:
		value = setting_value(details[name])
		if isinstance(value, bool) or not isinstance(value, (int, float)):
			raise TypeError(f"Particle group setting {name!r} must be numeric.")
		return float(value)

	def _vertex_data(self) -> bytes:
		vertices = np.concatenate(
			(
				self.positions.astype(np.float32),
				self.particle_colors,
				self.particle_surface_ids[:, None],
			),
			axis=1,
		)
		return vertices.tobytes(order="C")

	def apply_law(self, _dt: float) -> None:
		raise NotImplementedError

	def step(self, dt: float) -> None:
		if dt <= 0.0:
			return
		self.apply_law(dt)
		self._particle_buffer.write(self._vertex_data())

	def draw_simulation(self, view_projection: glm.mat4) -> None:
		matrix = struct.pack(
			"16f",
			*(
				float(view_projection[column][row])
				for column in range(4)
				for row in range(4)
			),
		)
		self._particle_program["u_view_projection"].write(  # type: ignore[union-attr]
			matrix
		)
		self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
		try:
			self._particle_vao.render(
				mode=self.PARTICLE_MODE,
				vertices=self.particle_count * self.POINT_VERTEX_COUNT,
			)
		finally:
			self.ctx.disable(moderngl.PROGRAM_POINT_SIZE)

	def cleanup(self) -> None:
		self._particle_vao.release()
		self._particle_buffer.release()
		self._particle_program.release()
		super().cleanup()
