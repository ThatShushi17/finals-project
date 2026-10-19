from __future__ import annotations

from pathlib import Path

import moderngl
import numpy as np
import pandas as pd

from src.engine.simulation.two.simulation_2d import Simulation2D
from src.engine.ui.color_scheme import ColorScheme
from src.enums import Accents
from src.settings import (
	CheckboxDetails,
	CompoundDetails,
	DropdownDetails,
	ListDetails,
	PresetDetails,
	Setting,
	SettingDetails,
	SliderDetails,
)
from src.types import SettingsSchema


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESET_PATH = PROJECT_ROOT / "data" / "presets" / "fluid_dynamics"
SHADER_ROOT = PROJECT_ROOT / "src" / "shaders" / "simulation"
PRESET_COLUMNS = (
	"mesh_type",
	"shape",
	"center_x",
	"center_y",
	"width",
	"height",
	"fx",
	"fy",
	"fz",
)
PRESET_COLUMN_SET = set(PRESET_COLUMNS)


def _set_uniform(
	program: moderngl.Program | moderngl.ComputeShader,
	name: str,
	value: object,
) -> None:
	program[name].value = value  # type: ignore


def _read_flow_preset(name: str) -> pd.DataFrame:
	path = PRESET_PATH / f"{name}.csv"
	if not path.is_file():
		raise FileNotFoundError(f"Fluid preset file not found: {path}")
	preset = pd.read_csv(path)
	missing_columns = PRESET_COLUMN_SET.difference(preset.columns)
	if missing_columns:
		raise ValueError(
			f"Fluid preset {path.name!r} is missing columns: "
			+ ", ".join(sorted(missing_columns))
		)
	return preset


def _mesh_details(name: str) -> CompoundDetails:
	return CompoundDetails(
		name=name,
		details={
			"shape": DropdownDetails(
				"Mesh Shape",
				setting=Setting("Circle"),
				options=("Circle", "Ellipse", "Rectangle"),
				placeholder_text="Circle",
				default_value="Circle",
			),
			"center_x": SliderDetails(
				"Center X",
				setting=Setting(0.5),
				lower_bound=0.0,
				upper_bound=1.0,
			),
			"center_y": SliderDetails(
				"Center Y",
				setting=Setting(0.5),
				lower_bound=0.0,
				upper_bound=1.0,
			),
			"width": SliderDetails(
				"Mesh Width",
				setting=Setting(0.12),
				lower_bound=0.02,
				upper_bound=0.8,
			),
			"height": SliderDetails(
				"Mesh Height",
				setting=Setting(0.12),
				lower_bound=0.02,
				upper_bound=0.8,
			),
		},
	)


def _flow_source_details() -> CompoundDetails:
	return CompoundDetails(
		name="Flow Source",
		details={
			"source_type": DropdownDetails(
				"Source Type",
				setting=Setting("Inflow Jet"),
				options=("Off", "Inflow Jet", "Force Field"),
				placeholder_text="Choose a flow source",
				default_value="Inflow Jet",
			),
			"shape": DropdownDetails(
				"Region Shape",
				setting=Setting("Rectangle"),
				options=("Circle", "Ellipse", "Rectangle"),
				placeholder_text="Choose a shape",
				default_value="Rectangle",
			),
			"center_x": SliderDetails(
				"Center X",
				setting=Setting(0.08),
				lower_bound=0.0,
				upper_bound=1.0,
			),
			"center_y": SliderDetails(
				"Center Y",
				setting=Setting(0.5),
				lower_bound=0.0,
				upper_bound=1.0,
			),
			"width": SliderDetails(
				"Region Width",
				setting=Setting(0.08),
				lower_bound=0.02,
				upper_bound=1.0,
			),
			"height": SliderDetails(
				"Region Height",
				setting=Setting(0.22),
				lower_bound=0.02,
				upper_bound=1.0,
			),
			"fx": SliderDetails(
				"Source X",
				setting=Setting(4.0),
				lower_bound=-5.0,
				upper_bound=5.0,
			),
			"fy": SliderDetails(
				"Source Y",
				setting=Setting(0.0),
				lower_bound=-5.0,
				upper_bound=5.0,
			),
			"fz": SliderDetails(
				"Vorticity",
				setting=Setting(2.5),
				lower_bound=-5.0,
				upper_bound=5.0,
			),
		},
	)


def _set_region_from_row(region: CompoundDetails, row: pd.Series) -> None:
	source_type = region.details["source_type"]
	if not isinstance(source_type, DropdownDetails):
		raise TypeError("Flow-source type must be a dropdown.")
	source_type.setting.value = str(row["mesh_type"])
	for key in ("shape", "center_x", "center_y", "width", "height", "fx", "fy", "fz"):
		detail = region.details[key]
		if key == "shape":
			if not isinstance(detail, DropdownDetails):
				raise TypeError(f"Flow-region property {key!r} must be a dropdown.")
			detail.setting.value = str(row[key]).title()
		else:
			if not isinstance(detail, SliderDetails):
				raise TypeError(f"Flow-region property {key!r} must be a slider.")
			detail.setting = Setting(float(str(row[key])))


def _set_mesh_from_row(mesh: CompoundDetails, row: pd.Series) -> None:
	for key in ("shape", "center_x", "center_y", "width", "height"):
		detail = mesh.details[key]
		if key == "shape":
			if not isinstance(detail, DropdownDetails):
				raise TypeError(f"Mesh property {key!r} must be a dropdown.")
			detail.setting.value = str(row[key]).title()
		else:
			if not isinstance(detail, SliderDetails):
				raise TypeError(f"Mesh property {key!r} must be a slider.")
			detail.setting = Setting(float(str(row[key])))


def _details_values(details: CompoundDetails) -> dict[str, str | float | bool]:
	values: dict[str, str | float | bool] = {}
	for name, detail in details.details.items():
		if isinstance(detail, DropdownDetails):
			values[name] = detail.setting.value
		elif isinstance(detail, SliderDetails):
			values[name] = float(detail.setting.value)
		elif isinstance(detail, CheckboxDetails):
			values[name] = detail.setting.value
		else:
			raise TypeError(f"Unsupported flow-region setting {name!r}.")
	return values


def _region_mask(
	x: np.ndarray,
	y: np.ndarray,
	values: dict[str, str | float | bool],
	grid_width: int,
	grid_height: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
	center_x = float(values["center_x"])
	center_y = float(values["center_y"])
	width = max(float(values["width"]), 1e-4)
	height = max(float(values["height"]), 1e-4)
	delta_x = x - center_x
	delta_y = y - center_y
	shape = str(values["shape"])
	if shape == "Circle":
		distance_x = delta_x * grid_width
		distance_y = delta_y * grid_height
		radius = min(width * grid_width, height * grid_height) * 0.5
		mask = distance_x**2 + distance_y**2 <= radius**2
	elif shape == "Ellipse":
		mask = (
			(delta_x / (width * 0.5)) ** 2
			+ (delta_y / (height * 0.5)) ** 2
			<= 1.0
		)
	elif shape == "Rectangle":
		mask = (
			(np.abs(delta_x) <= width * 0.5)
			& (np.abs(delta_y) <= height * 0.5)
		)
	else:
		raise ValueError(f"Unknown fluid region shape: {shape!r}")
	radial_x = delta_x / (width * 0.5)
	radial_y = delta_y / (height * 0.5)
	radial_length = np.maximum(
		np.sqrt(radial_x**2 + radial_y**2),
		1e-4,
	)
	return mask, -radial_y / radial_length, radial_x / radial_length


def _jet_outlet_values(
	values: dict[str, str | float | bool],
	grid_width: int,
	grid_height: int,
) -> dict[str, str | float | bool]:
	outlet = values.copy()
	fx = float(values["fx"])
	fy = float(values["fy"])
	speed = float(np.hypot(fx, fy))
	if speed == 0.0:
		return outlet

	direction_x = fx / speed
	direction_y = fy / speed
	width = max(float(values["width"]), 1e-4)
	height = max(float(values["height"]), 1e-4)
	if values["shape"] == "Rectangle":
		support = (
			abs(direction_x) * width * 0.5
			+ abs(direction_y) * height * 0.5
		)
	else:
		support = float(np.hypot(
			direction_x * width * 0.5,
			direction_y * height * 0.5,
		))
	cell_gap = float(np.hypot(
		direction_x / grid_width,
		direction_y / grid_height,
	))
	outlet["center_x"] = float(values["center_x"]) + direction_x * (
		support + cell_gap
	)
	outlet["center_y"] = float(values["center_y"]) + direction_y * (
		support + cell_gap
	)
	return outlet


class FluidDynamicsSimulation(Simulation2D):
	METRIC_PLOT_TITLE = "Fluid speed and tracer concentration"
	GRID_WIDTH = Setting[int](256)
	GRID_HEIGHT = Setting[int](160)
	VISCOSITY = Setting[float](0.002)
	CELL_SIZE = 2.0
	PRESSURE_ITERATIONS = 16
	WORKGROUP_SIZE = 16
	MAX_TIME_STEP = 1.0 / 30.0

	VELOCITY_SHADER = (
		SHADER_ROOT / "compute" / "fluid_velocity.comp"
	).read_text(encoding="utf-8")
	DIVERGENCE_SHADER = (
		SHADER_ROOT / "compute" / "fluid_divergence.comp"
	).read_text(encoding="utf-8")
	PRESSURE_SHADER = (
		SHADER_ROOT / "compute" / "fluid_pressure.comp"
	).read_text(encoding="utf-8")
	PROJECT_SHADER = (
		SHADER_ROOT / "compute" / "fluid_project.comp"
	).read_text(encoding="utf-8")
	DYE_SHADER = (
		SHADER_ROOT / "compute" / "fluid_dye.comp"
	).read_text(encoding="utf-8")
	FRAGMENT_SHADER = (
		SHADER_ROOT / "grid" / "fluid.frag"
	).read_text(encoding="utf-8")

	@classmethod
	def get_schema(cls) -> SettingsSchema:
		schema = super().get_schema()
		preset_paths = sorted(PRESET_PATH.glob("*.csv"))
		if not preset_paths:
			raise FileNotFoundError(
				f"No fluid preset CSV files found in {PRESET_PATH}."
			)
		preset_names = tuple(path.stem for path in preset_paths)
		default_preset = (
			"jet_channel"
			if "jet_channel" in preset_names
			else preset_names[0]
		)
		default_mesh_rows = _read_flow_preset(default_preset)
		mesh_rows = default_mesh_rows[
			default_mesh_rows["mesh_type"].astype(str) == "Obstacle"
		]
		meshes: list[SettingDetails] = [
			_mesh_details(f"Mesh {index + 1}")
			for index in range(len(mesh_rows))
		]

		def generate_mesh() -> SettingDetails:
			return _mesh_details(f"Mesh {len(meshes) + 1}")

		mesh_list = ListDetails(
			name="Obstacles",
			details=meshes,
			generation_callback=generate_mesh,
			initial_only=False,
		)
		for mesh, (_, row) in zip(
			meshes,
			mesh_rows.iterrows(),
		):
			if not isinstance(mesh, CompoundDetails):
				raise TypeError("Fluid meshes must be compound settings.")
			_set_mesh_from_row(mesh, row)

		flow_source = _flow_source_details()

		def apply_preset(name: str) -> None:
			preset = _read_flow_preset(name)
			obstacle_rows = preset[
				preset["mesh_type"].astype(str) == "Obstacle"
			]
			while len(mesh_list.details) < len(obstacle_rows):
				mesh_list.details.append(generate_mesh())
			while len(mesh_list.details) > len(obstacle_rows):
				mesh_list.details.pop()
			for mesh, (_, row) in zip(mesh_list.details, obstacle_rows.iterrows()):
				if not isinstance(mesh, CompoundDetails):
					raise TypeError("Fluid meshes must be compound settings.")
				_set_mesh_from_row(mesh, row)

			source_rows = preset[
				preset["mesh_type"].astype(str) != "Obstacle"
			]
			if len(source_rows) > 1:
				raise ValueError(
					f"Preset {name!r} can contain at most one flow source."
				)
			if source_rows.empty:
				source_type = flow_source.details["source_type"]
				if not isinstance(source_type, DropdownDetails):
					raise TypeError("Flow-source type must be a dropdown.")
				source_type.setting.value = "Off"
			else:
				_set_region_from_row(flow_source, source_rows.iloc[0])

		apply_preset(default_preset)
		schema.update({
			"preset": PresetDetails(
				"Flow Preset",
				setting=Setting(default_preset),
				options=preset_names,
				placeholder_text="Choose a flow preset",
				default_value=default_preset,
				initial_only=True,
				selection_callback=apply_preset,
			),
			"grid_width": SliderDetails(
				"Grid Width",
				setting=cls.GRID_WIDTH,
				lower_bound=64,
				upper_bound=512,
				initial_only=True,
			),
			"grid_height": SliderDetails(
				"Grid Height",
				setting=cls.GRID_HEIGHT,
				lower_bound=64,
				upper_bound=512,
				initial_only=True,
			),
			"viscosity": SliderDetails(
				"Viscosity",
				setting=cls.VISCOSITY,
				lower_bound=0.0,
				upper_bound=0.1,
			),
			"flow_source": flow_source,
			"meshes": mesh_list,
		})
		return schema

	def __init__(
		self,
		ctx: moderngl.Context,
		schema: SettingsSchema,
		color_scheme: ColorScheme,
	):
		super().__init__(ctx=ctx, schema=schema, color_scheme=color_scheme)
		self.grid_width = int(schema["grid_width"].setting.value)  # type: ignore
		self.grid_height = int(schema["grid_height"].setting.value)  # type: ignore
		self.camera_x = self.grid_width * self.CELL_SIZE / 2.0
		self.camera_y = self.grid_height * self.CELL_SIZE / 2.0
		self.cell_size = self.CELL_SIZE
		self._groups = (
			(self.grid_width + self.WORKGROUP_SIZE - 1) // self.WORKGROUP_SIZE,
			(self.grid_height + self.WORKGROUP_SIZE - 1) // self.WORKGROUP_SIZE,
		)
		self._velocity_textures = [
			self._create_texture(2, np.zeros((self.grid_height, self.grid_width, 2), dtype=np.float32)),
			self._create_texture(2, np.zeros((self.grid_height, self.grid_width, 2), dtype=np.float32)),
		]
		self._pressure_textures = [
			self._create_texture(1, np.zeros((self.grid_height, self.grid_width), dtype=np.float32)),
			self._create_texture(1, np.zeros((self.grid_height, self.grid_width), dtype=np.float32)),
		]
		self._divergence_texture = self._create_texture(
			1,
			np.zeros((self.grid_height, self.grid_width), dtype=np.float32),
		)
		self._dye_textures = [
			self._create_texture(1, np.zeros((self.grid_height, self.grid_width), dtype=np.float32)),
			self._create_texture(1, np.zeros((self.grid_height, self.grid_width), dtype=np.float32)),
		]
		self._source_texture = self._create_texture(
			4,
			np.zeros((self.grid_height, self.grid_width, 4), dtype=np.float32),
		)
		self._jet_mask_texture = self._create_texture(
			1,
			np.zeros((self.grid_height, self.grid_width), dtype=np.float32),
		)
		self._obstacle_texture = self._create_texture(
			1,
			np.zeros((self.grid_height, self.grid_width), dtype=np.float32),
		)
		self._dye_source_texture = self._create_texture(
			1,
			np.zeros((self.grid_height, self.grid_width), dtype=np.float32),
		)
		self._velocity_index = 0
		self._pressure_index = 0
		self._dye_index = 0
		self._velocity_program = ctx.compute_shader(self.VELOCITY_SHADER)
		self._divergence_program = ctx.compute_shader(self.DIVERGENCE_SHADER)
		self._pressure_program = ctx.compute_shader(self.PRESSURE_SHADER)
		self._project_program = ctx.compute_shader(self.PROJECT_SHADER)
		self._dye_program = ctx.compute_shader(self.DYE_SHADER)
		self._render_program = ctx.program(
			vertex_shader=self.VERTEX_SHADER,
			fragment_shader=self.FRAGMENT_SHADER,
		)
		self._render_vao = ctx.vertex_array(  # type: ignore[reportUnknownMemberType]
			self._render_program,
			[(self._quad_buffer, "2f", "in_position")],
		)
		self._rebuild_mesh_fields()

	def _create_texture(
		self,
		components: int,
		data: np.ndarray,
	) -> moderngl.Texture:
		texture = self.ctx.texture(
			(data.shape[1], data.shape[0]),
			components=components,
			data=data.astype(np.float32, copy=False).tobytes(order="C"),
			dtype="f4",
			alignment=1,
		)
		texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
		texture.repeat_x = False
		texture.repeat_y = False
		return texture

	def _run_compute(
		self,
		program: moderngl.ComputeShader,
		output: moderngl.Texture,
	) -> None:
		output.bind_to_image(0, read=False, write=True)
		program.run(group_x=self._groups[0], group_y=self._groups[1], group_z=1)
		self.ctx.memory_barrier()

	def _set_size(self, program: moderngl.ComputeShader) -> None:
		_set_uniform(program, "u_size", (self.grid_width, self.grid_height))

	def _rebuild_mesh_fields(self) -> None:
		mesh_details = self.schema["meshes"]
		if not isinstance(mesh_details, ListDetails):
			raise TypeError("Fluid dynamics requires a list of obstacle meshes.")
		y, x = np.mgrid[:self.grid_height, :self.grid_width]
		x = (x.astype(np.float32) + 0.5) / self.grid_width
		y = (y.astype(np.float32) + 0.5) / self.grid_height
		sources = np.zeros((self.grid_height, self.grid_width, 4), dtype=np.float32)
		jet_mask = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
		obstacles = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
		dye_sources = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)

		for mesh in mesh_details.details:
			if not isinstance(mesh, CompoundDetails):
				raise TypeError("Each obstacle must be a compound setting.")
			values = _details_values(mesh)
			mask, _, _ = _region_mask(
				x,
				y,
				values,
				self.grid_width,
				self.grid_height,
			)
			obstacles[mask] = 1.0

		field_details = self.schema["flow_source"]
		if not isinstance(field_details, CompoundDetails):
			raise TypeError("Fluid flow source must be a compound setting.")
		values = _details_values(field_details)
		source_type = str(values["source_type"])
		if source_type != "Off":
			mask, tangent_x, tangent_y = _region_mask(
				x,
				y,
				values,
				self.grid_width,
				self.grid_height,
			)
			fx = float(values["fx"])
			fy = float(values["fy"])
			vorticity = float(values["fz"])
			if source_type == "Inflow Jet":
				obstacles[mask] = 1.0
				outlet_values = _jet_outlet_values(
					values,
					self.grid_width,
					self.grid_height,
				)
				outlet_mask, outlet_tangent_x, outlet_tangent_y = _region_mask(
					x,
					y,
					outlet_values,
					self.grid_width,
					self.grid_height,
				)
				outlet_mask &= obstacles == 0.0
				sources[..., 2][outlet_mask] = (
					fx + outlet_tangent_x[outlet_mask] * vorticity
				)
				sources[..., 3][outlet_mask] = (
					fy + outlet_tangent_y[outlet_mask] * vorticity
				)
				jet_mask[outlet_mask] = 1.0
				dye_sources[outlet_mask] = 1.0
			elif source_type == "Force Field":
				sources[..., 0][mask] += fx + tangent_x[mask] * vorticity
				sources[..., 1][mask] += fy + tangent_y[mask] * vorticity
				dye_sources[mask] = 1.0
			else:
				raise ValueError(f"Unknown fluid source type: {source_type!r}")

		solid_cells = obstacles > 0.5
		sources[solid_cells] = 0.0
		jet_mask[solid_cells] = 0.0
		dye_sources[solid_cells] = 0.0
		self._source_texture.write(sources.tobytes(order="C"), alignment=1)
		self._jet_mask_texture.write(jet_mask.tobytes(order="C"), alignment=1)
		self._obstacle_texture.write(obstacles.tobytes(order="C"), alignment=1)
		self._dye_source_texture.write(
			dye_sources.astype(np.float32).tobytes(order="C"),
			alignment=1,
		)

	def _dispatch_velocity(self, dt: float) -> None:
		program = self._velocity_program
		current = self._velocity_textures[self._velocity_index]
		next_index = 1 - self._velocity_index
		output = self._velocity_textures[next_index]
		current.use(location=0)
		self._source_texture.use(location=1)
		self._jet_mask_texture.use(location=2)
		self._obstacle_texture.use(location=3)
		_set_uniform(program, "u_velocity", 0)
		_set_uniform(program, "u_mesh_sources", 1)
		_set_uniform(program, "u_jet_mask", 2)
		_set_uniform(program, "u_obstacles", 3)
		_set_uniform(program, "u_time_step", dt)
		viscosity_details = self.schema["viscosity"]
		if not isinstance(viscosity_details, SliderDetails):
			raise TypeError("Fluid viscosity must be a slider setting.")
		_set_uniform(program, "u_viscosity", float(viscosity_details.setting.value))
		self._set_size(program)
		self._run_compute(program, output)
		self._velocity_index = next_index

	def _dispatch_divergence(self) -> None:
		program = self._divergence_program
		self._velocity_textures[self._velocity_index].use(location=0)
		self._obstacle_texture.use(location=1)
		_set_uniform(program, "u_velocity", 0)
		_set_uniform(program, "u_obstacles", 1)
		self._set_size(program)
		self._run_compute(program, self._divergence_texture)

	def _dispatch_pressure(self) -> None:
		for _ in range(self.PRESSURE_ITERATIONS):
			program = self._pressure_program
			current_index = self._pressure_index
			next_index = 1 - current_index
			self._pressure_textures[current_index].use(location=0)
			self._divergence_texture.use(location=1)
			self._obstacle_texture.use(location=2)
			_set_uniform(program, "u_pressure", 0)
			_set_uniform(program, "u_divergence", 1)
			_set_uniform(program, "u_obstacles", 2)
			self._set_size(program)
			self._run_compute(program, self._pressure_textures[next_index])
			self._pressure_index = next_index

	def _dispatch_projection(self) -> None:
		program = self._project_program
		next_index = 1 - self._velocity_index
		self._velocity_textures[self._velocity_index].use(location=0)
		self._pressure_textures[self._pressure_index].use(location=1)
		self._obstacle_texture.use(location=2)
		_set_uniform(program, "u_velocity", 0)
		_set_uniform(program, "u_pressure", 1)
		_set_uniform(program, "u_obstacles", 2)
		self._set_size(program)
		self._run_compute(program, self._velocity_textures[next_index])
		self._velocity_index = next_index

	def _dispatch_dye(self, dt: float) -> None:
		program = self._dye_program
		next_index = 1 - self._dye_index
		self._dye_textures[self._dye_index].use(location=0)
		self._velocity_textures[self._velocity_index].use(location=1)
		self._dye_source_texture.use(location=2)
		self._obstacle_texture.use(location=3)
		_set_uniform(program, "u_dye", 0)
		_set_uniform(program, "u_velocity", 1)
		_set_uniform(program, "u_dye_source", 2)
		_set_uniform(program, "u_obstacles", 3)
		_set_uniform(program, "u_time_step", dt)
		self._set_size(program)
		self._run_compute(program, self._dye_textures[next_index])
		self._dye_index = next_index

	def step(self, dt: float) -> None:
		if dt <= 0.0:
			return
		substeps = max(1, int(np.ceil(dt / self.MAX_TIME_STEP)))
		substep = dt / substeps
		for _ in range(substeps):
			self._rebuild_mesh_fields()
			self._dispatch_velocity(substep)
			self._dispatch_divergence()
			self._dispatch_pressure()
			self._dispatch_projection()
			self._dispatch_dye(substep)

	def draw_gpu(self, view_size: tuple[int, int]) -> None:
		program = self._render_program
		self._velocity_textures[self._velocity_index].use(location=0)
		self._dye_textures[self._dye_index].use(location=1)
		self._obstacle_texture.use(location=2)
		_set_uniform(program, "u_velocity", 0)
		_set_uniform(program, "u_dye", 1)
		_set_uniform(program, "u_obstacles", 2)
		_set_uniform(program, "u_grid_size", (self.grid_width, self.grid_height))
		_set_uniform(program, "u_view_size", view_size)
		_set_uniform(program, "u_camera", (self.camera_x, self.camera_y))
		_set_uniform(program, "u_zoom", self.zoom)
		_set_uniform(program, "u_cell_size", self.cell_size)
		_set_uniform(program, "u_background", self._color_floats(
			self.color_scheme.bg_bold()
		))
		for uniform, accent in (
			("u_cool_color", Accents.BLUE),
			("u_mid_color", Accents.GREEN),
			("u_warm_color", Accents.ORANGE),
			("u_hot_color", Accents.PINK),
		):
			_set_uniform(program, uniform, self._color_floats(
				self.color_scheme.accent(accent)
			))
		_set_uniform(
			program,
			"u_outline_color",
			self._color_floats(self.color_scheme.fg_bold()),
		)
		self._render_vao.render(mode=moderngl.TRIANGLES, vertices=3)

	def get_metrics(self) -> dict[str, float]:
		velocity = np.frombuffer(
			self._velocity_textures[self._velocity_index].read(alignment=1),
			dtype=np.float32,
		).reshape((self.grid_height, self.grid_width, 2))
		dye = np.frombuffer(
			self._dye_textures[self._dye_index].read(alignment=1),
			dtype=np.float32,
		)
		return {
			"Mean Speed": float(np.mean(np.linalg.norm(velocity, axis=2))),
			"Mean Tracer": float(np.mean(dye)),
		}

	def cleanup(self) -> None:
		for texture in (
			*self._velocity_textures,
			*self._pressure_textures,
			self._divergence_texture,
			*self._dye_textures,
			self._source_texture,
			self._jet_mask_texture,
			self._obstacle_texture,
			self._dye_source_texture,
		):
			texture.release()
		for program in (
			self._velocity_program,
			self._divergence_program,
			self._pressure_program,
			self._project_program,
			self._dye_program,
			self._render_program,
			self._render_vao,
		):
			program.release()
		super().cleanup()
