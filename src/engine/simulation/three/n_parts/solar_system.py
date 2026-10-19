"""Solar-system preset data based on JPL's approximate J2000 planetary elements.

Source: https://ssd.jpl.nasa.gov/planets/approx_pos.html
"""

import numpy as np
import pandas as pd
from pathlib import Path

from .....settings import ListDetails, SettingDetails
from .particle_groups import ACCENT_OPTIONS


G_AU = 4.0 * np.pi**2
PLANETARY_DATA_PATH = (
	Path(__file__).resolve().parents[5]
	/ "data"
	/ "misc"
	/ "solar_system.csv"
)


def _set_group_value(
	group: SettingDetails,
	name: str,
	value: int | float | str,
) -> None:
	if not hasattr(group, "details"):
		raise TypeError("Gravity presets require compound particle groups.")
	details = group.details  # type: ignore[attr-defined]
	details[name].setting.value = value  # type: ignore[union-attr]


def apply_solar_system(groups: ListDetails) -> None:
	states = solar_system_initial_conditions()
	if len(groups.details) != len(states):
		raise ValueError("Solar-system preset has an unexpected particle group count.")

	for group, (name, mass, position, velocity, color_name) in zip(
		groups.details,
		states,
	):
		group.name = name  # type: ignore[attr-defined]
		for key, value in (
			("count", 1),
			("mass", mass),
			("position_x", position[0]),
			("position_y", position[1]),
			("position_z", position[2]),
			("velocity_x", velocity[0]),
			("velocity_y", velocity[1]),
			("velocity_z", velocity[2]),
			("color", color_name),
		):
			_set_group_value(group, key, value)
		if not hasattr(group, "accent"):
			raise TypeError("Gravity presets require compound particle groups.")
		group.accent = lambda key=color_name: ACCENT_OPTIONS[key]  # type: ignore[attr-defined]


def apply_scattered_cloud(groups: ListDetails) -> None:
	group_count = len(groups.details)
	for index, group in enumerate(groups.details):
		group.name = f"Cloud Group {index + 1}"  # type: ignore[attr-defined]
		angle = index * 2.0 * np.pi / group_count
		for key, value in (
			("count", 16),
			("mass", 0.01),
			("position_x", float(np.cos(angle))),
			("position_y", float(np.sin(angle))),
			("position_z", (index % 3 - 1) * 0.5),
			("velocity_x", 0.0),
			("velocity_y", 0.0),
			("velocity_z", 0.0),
		):
			_set_group_value(group, key, value)


def _rotate_orbit(
	vector: np.ndarray,
	inclination: float,
	ascending_node: float,
	argument_perihelion: float,
) -> np.ndarray:
	node = np.deg2rad(ascending_node)
	argument = np.deg2rad(argument_perihelion)
	inclination_radians = np.deg2rad(inclination)
	rotate_node = np.array([
		[np.cos(node), -np.sin(node), 0.0],
		[np.sin(node), np.cos(node), 0.0],
		[0.0, 0.0, 1.0],
	])
	rotate_inclination = np.array([
		[1.0, 0.0, 0.0],
		[0.0, np.cos(inclination_radians), -np.sin(inclination_radians)],
		[0.0, np.sin(inclination_radians), np.cos(inclination_radians)],
	])
	rotate_argument = np.array([
		[np.cos(argument), -np.sin(argument), 0.0],
		[np.sin(argument), np.cos(argument), 0.0],
		[0.0, 0.0, 1.0],
	])
	return rotate_node @ rotate_inclination @ rotate_argument @ vector


def solar_system_initial_conditions() -> list[
	tuple[str, float, np.ndarray, np.ndarray, str]
]:
	heliocentric_states: list[
		tuple[str, float, np.ndarray, np.ndarray, str]
	] = []
	planetary_data = pd.read_csv(PLANETARY_DATA_PATH)
	required_columns = {
		"name",
		"mass_solar",
		"semi_major_axis_au",
		"eccentricity",
		"inclination_deg",
		"ascending_node_deg",
		"longitude_perihelion_deg",
		"mean_longitude_deg",
		"color",
	}
	missing_columns = required_columns.difference(planetary_data.columns)
	if missing_columns:
		raise ValueError(
			"Solar-system data is missing required columns: "
			+ ", ".join(sorted(missing_columns))
		)
	for (
		name,
		mass,
		semi_major_axis,
		eccentricity,
		inclination,
		ascending_node,
		longitude_perihelion,
		mean_longitude,
		color_name,
	) in planetary_data[[
		"name",
		"mass_solar",
		"semi_major_axis_au",
		"eccentricity",
		"inclination_deg",
		"ascending_node_deg",
		"longitude_perihelion_deg",
		"mean_longitude_deg",
		"color",
	]].itertuples(index=False, name=None):
		name = str(name)
		mass = float(mass)
		semi_major_axis = float(semi_major_axis)
		eccentricity = float(eccentricity)
		inclination = float(inclination)
		ascending_node = float(ascending_node)
		longitude_perihelion = float(longitude_perihelion)
		mean_longitude = float(mean_longitude)
		color_name = str(color_name)
		if semi_major_axis == 0.0:
			heliocentric_states.append(
				(name, mass, np.zeros(3), np.zeros(3), color_name)
			)
			continue

		argument_perihelion = longitude_perihelion - ascending_node
		mean_anomaly = np.deg2rad(mean_longitude - longitude_perihelion)
		eccentric_anomaly = mean_anomaly
		for _ in range(8):
			eccentric_anomaly -= (
				eccentric_anomaly
				- eccentricity * np.sin(eccentric_anomaly)
				- mean_anomaly
			) / (
				1.0 - eccentricity * np.cos(eccentric_anomaly)
			)

		cos_e = np.cos(eccentric_anomaly)
		sin_e = np.sin(eccentric_anomaly)
		factor = np.sqrt(1.0 - eccentricity**2)
		position_orbital = semi_major_axis * np.array([
			cos_e - eccentricity,
			factor * sin_e,
			0.0,
		])
		orbital_speed = np.sqrt(G_AU / semi_major_axis) / (
			1.0 - eccentricity * cos_e
		)
		velocity_orbital = orbital_speed * np.array([
			-sin_e,
			factor * cos_e,
			0.0,
		])
		heliocentric_states.append((
			name,
			mass,
			_rotate_orbit(
				position_orbital,
				inclination,
				ascending_node,
				argument_perihelion,
			),
			_rotate_orbit(
				velocity_orbital,
				inclination,
				ascending_node,
				argument_perihelion,
			),
			color_name,
		))

	total_mass = sum(state[1] for state in heliocentric_states)
	center_of_mass = sum(
		(mass * position for _, mass, position, _, _ in heliocentric_states),
		start=np.zeros(3),
	) / total_mass
	center_velocity = sum(
		(mass * velocity for _, mass, _, velocity, _ in heliocentric_states),
		start=np.zeros(3),
	) / total_mass
	return [
		(name, mass, position - center_of_mass, velocity - center_velocity, color)
		for name, mass, position, velocity, color in heliocentric_states
	]
