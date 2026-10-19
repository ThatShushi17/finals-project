from .....enums import Accents
from .....settings import (
	CompoundDetails,
	DropdownDetails,
	ListDetails,
	Setting,
	SettingDetails,
	SliderDetails,
)


ACCENT_OPTIONS = {
	"blue": Accents.BLUE,
	"green": Accents.GREEN,
	"orange": Accents.ORANGE,
	"pink": Accents.PINK,
}


def create_particle_group(
	name: str,
	position: tuple[float, float, float] = (0.0, 0.0, 0.0),
	color_name: str = "blue",
) -> CompoundDetails:
	color_setting = Setting(color_name)
	details: dict[str, SettingDetails] = {
		"count": SliderDetails(
			"Particle Count",
			setting=Setting(64),
			lower_bound=1,
			upper_bound=512,
			initial_only=True,
		),
		"mass": SliderDetails(
			"Mass per Particle",
			setting=Setting(1.0),
			lower_bound=1e-10,
			upper_bound=10.0,
			initial_only=True,
		),
		"position_x": SliderDetails(
			"Center X",
			setting=Setting(position[0]),
			lower_bound=-2.0,
			upper_bound=2.0,
			initial_only=True,
		),
		"position_y": SliderDetails(
			"Center Y",
			setting=Setting(position[1]),
			lower_bound=-2.0,
			upper_bound=2.0,
			initial_only=True,
		),
		"position_z": SliderDetails(
			"Center Z",
			setting=Setting(position[2]),
			lower_bound=-2.0,
			upper_bound=2.0,
			initial_only=True,
		),
		"velocity_x": SliderDetails(
			"Velocity X",
			setting=Setting(0.0),
			lower_bound=-2.0,
			upper_bound=2.0,
			initial_only=True,
		),
		"velocity_y": SliderDetails(
			"Velocity Y",
			setting=Setting(0.0),
			lower_bound=-2.0,
			upper_bound=2.0,
			initial_only=True,
		),
		"velocity_z": SliderDetails(
			"Velocity Z",
			setting=Setting(0.0),
			lower_bound=-2.0,
			upper_bound=2.0,
			initial_only=True,
		),
		"color": DropdownDetails(
			"Particle Color",
			setting=color_setting,
			options=tuple(ACCENT_OPTIONS),
			placeholder_text=color_name,
			default_value=color_name,
			initial_only=True,
		),
	}
	return CompoundDetails(
		name=name,
		details=details,
		initial_only=True,
		accent=lambda setting=color_setting: ACCENT_OPTIONS[setting.value],
	)


def create_particle_group_list(
	initial_groups: int = 1,
) -> ListDetails:
	groups = [
		create_particle_group(
			f"Particle Group {index + 1}",
			position=(-0.75 + index * 1.5, 0.0, 0.0),
			color_name=tuple(ACCENT_OPTIONS)[index % len(ACCENT_OPTIONS)],
		)
		for index in range(initial_groups)
	]

	def generate_group() -> CompoundDetails:
		index = len(groups)
		group = create_particle_group(
			f"Particle Group {index + 1}",
			position=(-0.75 + index * 1.5, 0.0, 0.0),
			color_name=tuple(ACCENT_OPTIONS)[index % len(ACCENT_OPTIONS)],
		)
		return group

	return ListDetails(
		name="Particle Groups",
		details=groups,
		generation_callback=generate_group,
		initial_only=True,
	)


def setting_value(details: SettingDetails) -> object:
	if isinstance(details, (DropdownDetails, SliderDetails)):
		return details.setting.value
	raise TypeError(f"Setting {details.name!r} does not store a scalar value.")
