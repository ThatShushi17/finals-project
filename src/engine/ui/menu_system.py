import pygame
from collections.abc import Callable

from ...settings import (
	CheckboxDetails,
	CompoundDetails,
	DropdownDetails,
	InputDetails,
	ListDetails,
	PresetDetails,
	SettingDetails,
	SliderDetails,
)
from ..frame_data import FrameData
from .component import Component
from .components import Tab, TabHandler, Container, Button, Label, Slider, Input, Checkbox, Dropdown
from .font_handler import FontHandler
from .color_scheme import ColorScheme

from ...types import Colorlike, Dual, FiendCallback, SettingsSchema
from ...enums import Alignment, Axis, TabStyles, Accents, HexFadeCorner, TabBackgrounds

class TabCreationOutput(Tab):
	def __init__(self, tab: Tab, containers: list[Container]):
		super().__init__(
			handler=tab.handler,
			background_color=tab.background_color,
			home=tab.home,
			background=tab.background,
			children=tab.children,
			hex_fade_corner=tab.hex_fade_corner
		)
		self.containers = containers
		
	@property
	def main_container(self):
		return self.containers[0]

class MenuSystem:
	def __init__(
		self,
		frame_data: FrameData,
		font_handler: FontHandler,
		color_scheme: ColorScheme,
		window_size: Dual
	):
		self.frame_data = frame_data
		self.font_handler = font_handler
		self.color_scheme = color_scheme

		self.surf = pygame.Surface(window_size, pygame.SRCALPHA)
		self.root = Component((0, 0), window_size)
		self.tab_handler = TabHandler(self.root, frame_data)

	def update(self):
		self.tab_handler.update(self.frame_data)

	def render(self):
		self.surf.fill((0, 0, 0, 0))

		self.tab_handler.draw(self.surf)

		return self.surf

	def new_container(
		self,
		axis: Axis = Axis.VERTICAL,
		cross_length: int = 0,
		cross_percent: float = 0.8,
		alignment: Alignment = Alignment.CENTER,
		background_color: Colorlike | Callable[[], Colorlike] | None = None,
		fit_content: bool = False,
	) -> Container:
		return Container(
			axis=axis,
			cross_length=cross_length,
			cross_percent=cross_percent,
			alignment=alignment,
			background_color=background_color,
			scrollbar_handle_color=self.color_scheme.fg_bold,
			scrollbar_accent_color=lambda: self.color_scheme.accent(Accents.PINK),
			scrollbar_track_color=self.color_scheme.fg,
			fit_content=fit_content,
		)

	def new_tab(
		self,
		type: TabStyles,
		title: str | None,
		background: TabBackgrounds = TabBackgrounds.SOLID,
		accent: Accents = Accents.PINK,
		hex_fade_corner: HexFadeCorner = HexFadeCorner.BOTTOM_LEFT,
	) -> TabCreationOutput:
		if title is not None:
			title_label = Label(
				relative_position=(0, 0),
				text_source=title,
				font=self.font_handler.get_heading(),
				color=self.color_scheme.fg_bold if background != TabBackgrounds.MAIN else "#FCFAF8"
			)
			title_label.margin_after = 50
		
		match type:
			case TabStyles.ONE_CONTAINER:
				tab = Tab(
					handler=self.tab_handler,
					background_color=self.color_scheme.bg,
					background=(background, lambda a=accent: self.color_scheme.accent(a)),
					hex_fade_corner=hex_fade_corner,
				)

				container = self.new_container()
				if title is not None: container.add_child(title_label)  # type: ignore
				tab.add_child(container)

				return TabCreationOutput(tab=tab, containers=[container])

			case TabStyles.TWO_CONTAINERS:
				tab = Tab(
					handler=self.tab_handler,
					background_color=self.color_scheme.bg,
					background=(background, lambda a=accent: self.color_scheme.accent(a)),
					hex_fade_corner=hex_fade_corner,
				)
				
				main_container = self.new_container(cross_length=0, cross_percent=1)
				if title is not None: main_container.add_child(title_label)  # type: ignore
				tab.add_child(main_container)

				columns_container = self.new_container(Axis.HORIZONTAL, cross_length=0, cross_percent=0.8)
				main_container.add_child(columns_container)

				left_column = self.new_container(cross_length=0, cross_percent=0.4)
				left_column.margin_after = 40
				columns_container.add_child(left_column)
				
				right_column = self.new_container(cross_length=0, cross_percent=0.4)
				right_column.margin_after = 0
				columns_container.add_child(right_column)

				return TabCreationOutput(tab=tab, containers=[left_column, right_column])

	def add_button_list(
		self, 
		container: Container,
		*button_details: tuple[str, FiendCallback | None, Accents]
	):
		for name, callback, accent in button_details:
			btn = Button(
				relative_position=(0, 0),
				min_width=200,
				text_source=name,
				callback=callback if callback is not None else lambda: None,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg_bold,
				background_color=self.color_scheme.bg_bold,
				hover_color=lambda a=accent: self.color_scheme.accent(a),
				hover_text_color=self.color_scheme.fg_hover,
				border_color=self.color_scheme.bg_border
			)
			btn.margin_after = 20
			container.add_child(btn)

	def add_settings_from_schema(
		self,
		container: Container,
		schema: SettingsSchema,
		include_all: bool = True
	):
		for _, details in schema.items():
			self._add_setting_detail(container, details, include_all)

	def _add_setting_detail(
		self,
		container: Container,
		details: SettingDetails,
		include_all: bool = True,
		inherited_opacity: float = 1.0,
	):
		if details.initial_only and not include_all:
			return

		if isinstance(details, CompoundDetails):
			accent = details.accent or Accents.BLUE
			if callable(accent):
				accent_source = accent
			else:
				accent_source = lambda a=accent: a
			compound = self.new_container(
				cross_percent=0.9,
				fit_content=True,
				background_color=lambda source=accent_source, alpha=(
					details.opacity * inherited_opacity
				): self._with_opacity(
					self.color_scheme.accent(source()),
					alpha,
				),
			)
			compound.margin_after = 24
			title = Label(
				relative_position=(0, 0),
				text_source=lambda d=details: d.name,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg_bold,
			)
			title.margin_after = 16
			compound.add_child(title)
			for child_details in details.details.values():
				self._add_setting_detail(
					compound,
					child_details,
					include_all,
					details.opacity * inherited_opacity,
				)
			container.add_child(compound)
			return

		if isinstance(details, ListDetails):
			list_container = self.new_container(cross_percent=0.95)
			title = Label(
				relative_position=(0, 0),
				text_source=lambda d=details: d.name,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg_bold,
			)
			title.margin_after = 16
			list_container.add_child(title)

			for item in details.details:
				self._add_setting_detail(
					list_container,
					item,
					include_all,
					inherited_opacity,
				)

			def add_generated_detail() -> None:
				new_detail = details.generation_callback()
				details.details.append(new_detail)
				self._add_setting_detail(
					list_container,
					new_detail,
					include_all=True,
					inherited_opacity=inherited_opacity,
				)
				generated_component = list_container.children.pop()
				list_container.children.insert(-1, generated_component)

			self.add_button_list(
				list_container,
				(f"Add {details.name.removesuffix('s')}", add_generated_detail, Accents.GREEN),
			)
			container.add_child(list_container)
			return

		if isinstance(details, SliderDetails):
			fmt = ".0f" if isinstance(details.lower_bound, int) and isinstance(details.upper_bound, int) else ".4f"
			label = Label(
				relative_position=(0, 0),
				text_source=lambda d=details, f=fmt: f"{d.name}: {d.setting.value:{f}}",
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg
			)
			label.margin_after = 10
			slider = Slider(
				relative_position=(0, 0),
				width=200,
				initial_value=details.setting.value,  # type: ignore
				lower_bound=details.lower_bound,
				upper_bound=details.upper_bound,
				on_change=lambda val, d=details: setattr(d.setting, 'value', val),
				accent_color=lambda: self.color_scheme.accent(Accents.PINK),
				border_color=self.color_scheme.bg_border,
			)
			setattr(slider, "_setting_details", details)
			slider.margin_after = 30
			container.add_child(label, slider)
		elif isinstance(details, CheckboxDetails):
			label = Label(
				relative_position=(0, 0),
				text_source=details.name,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg
			)
			label.margin_after = 10
			checkbox = Checkbox(
				relative_position=(0, 0),
				size=(20, 20),
				initial_value=details.initial_value,
				on_change=lambda val, d=details: setattr(d.setting, 'value', val),
				accent_color=lambda: self.color_scheme.accent(Accents.PINK),
			)
			checkbox.margin_after = 30
			container.add_child(label, checkbox)
		elif isinstance(details, InputDetails):
			label = Label(
				relative_position=(0, 0),
				text_source=details.name,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg
			)
			label.margin_after = 10
			input_control = Input(
				relative_position=(0, 0),
				width=200,
				placeholder_text=details.placeholder_text,
				numeric_only=details.numeric_only,
				font=self.font_handler.get_font(),
				on_change=lambda val, d=details: setattr(d.setting, 'value', val),  # type: ignore
				accent_color=lambda: self.color_scheme.accent(Accents.PINK),
				border_color=self.color_scheme.bg_border,
			)
			input_control.margin_after = 30
			container.add_child(label, input_control)
		elif isinstance(details, PresetDetails):
			label = Label(
				relative_position=(0, 0),
				text_source=details.name,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg
			)
			label.margin_after = 10

			def apply_preset(
				value: str,
				preset_details: PresetDetails = details,
				root_container: Container = container,
			) -> None:
				preset_details.setting.value = value
				preset_details.selection_callback(value)
				self._sync_setting_controls(root_container)

			dropdown = Dropdown(
				relative_position=(0, 0),
				min_width=200,
				options=details.options,
				placeholder_text=details.placeholder_text,
				font=self.font_handler.get_font(),
				default_value=details.setting.value,
				on_change=apply_preset,
				accent_color=lambda: self.color_scheme.accent(Accents.PINK),
				border_color=self.color_scheme.bg_border,
			)
			setattr(dropdown, "_setting_details", details)
			dropdown.margin_after = 30
			container.add_child(label, dropdown)
		elif isinstance(details, DropdownDetails):
			label = Label(
				relative_position=(0, 0),
				text_source=details.name,
				font=self.font_handler.get_font(),
				color=self.color_scheme.fg
			)
			label.margin_after = 10
			dropdown = Dropdown(
				relative_position=(0, 0),
				min_width=200,
				options=details.options,
				placeholder_text=details.placeholder_text,
				font=self.font_handler.get_font(),
				default_value=details.default_value,
				on_change=lambda val, d=details: setattr(d.setting, 'value', val),
				accent_color=lambda: self.color_scheme.accent(Accents.PINK),
				border_color=self.color_scheme.bg_border,
			)
			setattr(dropdown, "_setting_details", details)
			dropdown.margin_after = 30
			container.add_child(label, dropdown)

	def _sync_setting_controls(self, component: Component) -> None:
		details = getattr(component, "_setting_details", None)
		if isinstance(details, SliderDetails) and isinstance(component, Slider):
			component.value = details.setting.value
		elif isinstance(details, DropdownDetails) and isinstance(component, Dropdown):
			component.value = details.setting.value
		for child in component.children:
			self._sync_setting_controls(child)

	@staticmethod
	def _with_opacity(color: Colorlike, opacity: float) -> pygame.Color:
		resolved = pygame.Color(color)
		resolved.a = round(resolved.a * max(0.0, min(opacity, 1.0)))
		return resolved
			