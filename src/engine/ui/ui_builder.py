from __future__ import annotations

import moderngl
import importlib.util
import pandas as pd
from pathlib import Path
from typing import TYPE_CHECKING

from ...settings import Settings
from .components import Button, Container, Label, Tab, Position, Frame, Plot
from .menu_system import MenuSystem

from ...types import FiendCallback, SettingsSchema
from ...enums import (
    Alignment,
    Axis,
    TabStyles,
    Accents,
    HexFadeCorner,
    TabBackgrounds,
)

if TYPE_CHECKING:
    from ..simulation.simulation import Simulation


class UIBuilder:
    def __init__(self,
        menu_system: MenuSystem,
        ctx: moderngl.Context
    ):
        self.menu_system = menu_system
        self.ctx = ctx
        self.frame = None
        self.energy_plot = None
        self.active_simulation: Simulation | None = None
        self.active_simulation_tab: Tab | None = None
        self._simulation_cleanup_pending = False

    def create_ui(self, exit_callback: FiendCallback, settings: Settings):
        tab_handler = self.menu_system.tab_handler

        main_tab = self.menu_system.new_tab(
            TabStyles.ONE_CONTAINER,
            None,
            background=TabBackgrounds.MAIN
        )

        settings_tab = self._settings_menu(main_tab, settings)
        self.select_simulation_tab = self._select_simulation_menu(main_tab, settings)

        title = Label(
            relative_position=(0, 72),
            text_source="Science Simulations",
            font=self.menu_system.font_handler.get_bold(
                int(self.menu_system.font_handler.default_size * 3)
            ),
            color="#FCFAF8",
            anchor=Position.TOP_CENTER,
            dock=Position.TOP_CENTER,
        )
        button_row = Container(
            axis=Axis.HORIZONTAL,
            cross_length=104,
            alignment=Alignment.SPACE_AROUND,
            background_color=None,
            cross_padding=0,
        )
        button_row.relative_position = (0, -32)
        button_row.anchor = Position.BOTTOM_CENTER
        button_row.dock = Position.BOTTOM_CENTER
        self.menu_system.add_button_list(
            button_row,
            ("Select Simulation", lambda: tab_handler.shove(self.select_simulation_tab), Accents.GREEN),
            ("View Graphs", lambda: self._open_view_graphs(main_tab), Accents.GREEN),
            ("Settings", lambda: tab_handler.shove(settings_tab), Accents.GREEN),
            ("Exit App", exit_callback, Accents.PINK)
        )
        for button in button_row.children:
            if isinstance(button, Button):
                button.min_width = 240
                button.margin_after = 28

        main_tab.children.clear()
        main_tab.add_child(title, button_row)

        tab_handler.push(main_tab)

    @staticmethod
    def _readings_directory() -> Path:
        return Path(__file__).resolve().parents[3] / "data" / "readings"

    @staticmethod
    def _display_name(path: Path) -> str:
        return path.stem.replace("_", " ").title()

    def _open_view_graphs(self, main_tab: Tab) -> None:
        graphs_tab = self._view_graphs_menu(main_tab)
        self.menu_system.tab_handler.shove(graphs_tab)

    def _view_graphs_menu(self, main_tab: Tab) -> Tab:
        graphs_tab = self.menu_system.new_tab(
            TabStyles.ONE_CONTAINER,
            "Recorded Simulations",
            background=TabBackgrounds.HEX,
            accent=Accents.BLUE
        )

        readings_dir = self._readings_directory()
        simulation_directories = sorted(
            (path for path in readings_dir.iterdir() if path.is_dir()),
            key=lambda path: path.name.casefold(),
        ) if readings_dir.is_dir() else []
        buttons: list[tuple[str, FiendCallback | None, Accents]] = [
            (
                self._display_name(directory),
                lambda d=directory, t=graphs_tab: self._open_recordings_menu(d, t),
                Accents.BLUE,
            )
            for directory in simulation_directories
        ]
        buttons.append(
            ("Back", lambda: self.menu_system.tab_handler.reverse_shove(), Accents.PINK)
        )
        self.menu_system.add_button_list(
            graphs_tab.main_container,
            *buttons,
        )

        return graphs_tab

    def _open_recordings_menu(self, simulation_directory: Path, parent_tab: Tab) -> None:
        tab_handler = self.menu_system.tab_handler
        recordings_tab = self.menu_system.new_tab(
            TabStyles.ONE_CONTAINER,
            f"{self._display_name(simulation_directory)} Recordings",
            background=TabBackgrounds.HEX,
            accent=Accents.BLUE,
        )
        self._populate_recordings_menu(simulation_directory, recordings_tab)
        tab_handler.push_immediate(recordings_tab)

    def _populate_recordings_menu(
        self,
        simulation_directory: Path,
        recordings_tab: Tab,
    ) -> None:
        tab_handler = self.menu_system.tab_handler
        recordings = sorted(
            (path for path in simulation_directory.glob("*.csv") if path.is_file()),
            key=lambda path: path.name.casefold(),
        )
        buttons: list[tuple[str, FiendCallback | None, Accents]] = [
            (
                filepath.stem.replace("_", " ").title(),
                lambda f=filepath, d=simulation_directory, t=recordings_tab: (
                    self._open_graph_detail(f, d, t)
                ),
                Accents.BLUE,
            )
            for filepath in recordings
        ]
        buttons.append(
            ("Back", lambda: tab_handler.pop_immediate(), Accents.PINK)
        )
        self.menu_system.add_button_list(recordings_tab.main_container, *buttons)

    def _delete_recording(
        self,
        filepath: Path,
        simulation_directory: Path,
        recordings_tab: Tab,
    ) -> None:
        filepath.unlink()
        recordings_tab.main_container.children.clear()
        self._populate_recordings_menu(simulation_directory, recordings_tab)
        self.menu_system.tab_handler.reverse_shove()

    def _get_recording_setting_names(self, simulation_directory: Path) -> set[str]:
        simulation_file = (
            Path(__file__).resolve().parents[2]
            / "simulations"
            / f"{simulation_directory.name}.py"
        )
        if not simulation_file.is_file():
            return set()

        module_name = f"_recorded_simulation_{simulation_directory.name}"
        spec = importlib.util.spec_from_file_location(module_name, simulation_file)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load simulation module from {simulation_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        from ..simulation.simulation import Simulation

        simulation_class = next(
            (
                candidate
                for candidate in vars(module).values()
                if isinstance(candidate, type)
                and issubclass(candidate, Simulation)
                and candidate.__module__ == module_name
            ),
            None,
        )
        if simulation_class is None:
            raise ValueError(f"No Simulation subclass found in {simulation_file}")
        return {
            details.name
            for details in simulation_class.get_schema().values()
            if not details.initial_only
        }

    def _open_graph_detail(
        self,
        filepath: Path,
        simulation_directory: Path,
        parent_tab: Tab,
    ) -> None:
        dataframe = pd.read_csv(filepath)
        time_column = (
            "Simulation time (s)"
            if "Simulation time (s)" in dataframe.columns
            else None
        )
        x_values = (
            dataframe[time_column].to_numpy()
            if time_column is not None
            else list(range(len(dataframe)))
        )
        x_label = "Simulation time (s)" if time_column else "Sample"
        setting_names = self._get_recording_setting_names(simulation_directory)
        numeric_columns = dataframe.select_dtypes(include="number").columns
        setting_columns = [
            column for column in numeric_columns
            if column in setting_names
        ]
        metric_columns = [
            column for column in numeric_columns
            if column != time_column and column not in setting_columns
        ]

        detail_tab = self.menu_system.new_tab(
            TabStyles.ONE_CONTAINER,
            filepath.stem.replace("_", " ").title(),
            background=TabBackgrounds.HEX,
            accent=Accents.BLUE,
            hex_fade_corner=HexFadeCorner.TOP_LEFT
        )
        metrics_plot = Plot((0, 0), height=250, anchor=Position.CENTER, dock=Position.CENTER)
        metrics_plot.ax.set_title(f"{self._display_name(simulation_directory)} metrics")
        metrics_plot.ax.set_xlabel(x_label)
        metrics_plot.ax.set_ylabel("Metric value")
        for column in metric_columns:
            metrics_plot.ax.plot(x_values, dataframe[column].to_numpy(), label=column)
        if metric_columns:
            metrics_plot.ax.legend(loc="upper right", fontsize=8)

        settings_plot = Plot((0, 0), height=250, anchor=Position.CENTER, dock=Position.CENTER)
        settings_plot.ax.set_title("Settings over time")
        settings_plot.ax.set_xlabel(x_label)
        settings_plot.ax.set_ylabel("Normalized value (0-1)")
        settings_plot.ax.set_ylim(0.0, 1.0)
        for column in setting_columns:
            settings_plot.ax.plot(x_values, dataframe[column].to_numpy(), label=column)
        if setting_columns:
            settings_plot.ax.legend(loc="upper right", fontsize=8)

        metrics_plot.margin_after = 20
        settings_plot.margin_after = 20
        detail_tab.main_container.add_child(metrics_plot, settings_plot)
        self.menu_system.add_button_list(
            detail_tab.main_container,
            (
                "Delete Recording",
                lambda f=filepath, d=simulation_directory, t=parent_tab: (
                    self._delete_recording(f, d, t)
                ),
                Accents.PINK,
            ),
            ("Back", lambda: self.menu_system.tab_handler.reverse_shove(), Accents.PINK),
        )
        self.menu_system.tab_handler.shove(detail_tab)

    def _select_simulation_menu(self, main_tab: Tab, settings: Settings):
        tab_handler = self.menu_system.tab_handler

        self.select_simulation_tab = self.menu_system.new_tab(
            TabStyles.ONE_CONTAINER,
            "Choose Simulation",
            background=TabBackgrounds.HEX,
            accent=Accents.ORANGE
        )

        buttons_tba: list[tuple[str, FiendCallback | None, Accents]] = []

        sim_dir = Path(__file__).resolve().parent.parent.parent / "simulations"
        if sim_dir.exists() and sim_dir.is_dir():
            for filepath in sim_dir.glob("*.py"):
                buttons_tba.append((filepath.stem.replace("_", " ").title(), lambda m=main_tab, s=settings, f=filepath: self._open_simulation_config(f, m, s), Accents.ORANGE))

        buttons_tba.append(("Back", lambda: tab_handler.reverse_shove(), Accents.PINK))

        self.menu_system.add_button_list(
            self.select_simulation_tab.main_container,
            *buttons_tba
        )

        return self.select_simulation_tab

    def _open_simulation_config(self, filepath: Path, main_tab: Tab, settings: Settings):
        from ..simulation.simulation import Simulation

        config_tab = self.menu_system.new_tab(
            TabStyles.TWO_CONTAINERS,
            filepath.stem.replace("_", " ").title(),
            background=TabBackgrounds.HEX,
            accent=Accents.ORANGE,
            hex_fade_corner=HexFadeCorner.TOP_LEFT,
        )
        config_tab.containers[0].background_color = self.menu_system.color_scheme.bg_bold

        spec = importlib.util.spec_from_file_location("sim_module", str(filepath))
        assert spec is not None and spec.loader is not None, f"Invalid module or missing loader for {filepath}"
        sim_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sim_module)

        sim_class = None
        for attr_name in dir(sim_module):
            attr = getattr(sim_module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Simulation) and attr.__module__ == sim_module.__name__:
                sim_class = attr
                break

        if not sim_class:
            print(f"Error: No subclass of Simulation found in {filepath}")
            return

        schema = sim_class.get_schema()
        user_settings_schema = settings.expose_schema()
        schema["fps"] = user_settings_schema["fps"]
        schema["data_collection_interval"] = user_settings_schema[
            "data_collection_interval"
        ]
        self.menu_system.add_settings_from_schema(
            config_tab.containers[0],
            schema
        )
        self.menu_system.add_button_list(
            config_tab.containers[1],
            (
                "Launch Simulation",
                lambda c=sim_class, s=schema, n=filepath.stem: self._launch_simulation(c, s, n),
                Accents.GREEN,
            ),
            ("Back", lambda: self.menu_system.tab_handler.reverse_shove(), Accents.PINK)
        )

        self.menu_system.tab_handler.shove(config_tab)

    def _launch_simulation(
        self,
        sim_class: type[Simulation],
        schema: SettingsSchema,
        simulation_name: str | None = None,
    ):
        simulation_tab, frame, metric_plot, setting_plot = self._simulation_view_menu(schema)

        simulation = sim_class(
            ctx=self.ctx,
            schema=schema,
            color_scheme=self.menu_system.color_scheme,
        )
        simulation.simulation_name = (
            simulation_name
            if simulation_name is not None
            else sim_class.__module__.rsplit(".", 1)[-1]
        )
        frame.simulation = simulation
        self.active_simulation = simulation
        self.active_simulation_tab = simulation_tab
        self._simulation_cleanup_pending = False
        metric_plot.set_live_data_source(
            lambda: (
                list(simulation.metric_history_times),
                simulation.get_metric_series(),
            ),
            title=getattr(
                simulation,
                "METRIC_PLOT_TITLE",
                f"{sim_class.__name__.removesuffix('Simulation')} metrics",
            ),
            revision_source=lambda: simulation.history_revision,
        )
        setting_plot.set_live_data_source(
            lambda: (list(simulation.history_times), simulation.get_setting_series()),
            title="Live simulation settings",
            y_label="Normalized value (0-1)",
            y_limits=(0.0, 1.0),
            revision_source=lambda: simulation.history_revision,
        )
        self.menu_system.tab_handler.open(simulation_tab)

    def _close_sim(self):
        self._simulation_cleanup_pending = True
        self.menu_system.tab_handler.close_to(self.select_simulation_tab)

    def cleanup_active_simulation(self) -> None:
        if self.active_simulation is None:
            return
        self.active_simulation.cleanup()
        self.active_simulation = None
        self.active_simulation_tab = None
        self._simulation_cleanup_pending = False

    def cleanup_inactive_simulation(self) -> None:
        if (
            self._simulation_cleanup_pending
            and self.active_simulation_tab is not None
            and not self.menu_system.tab_handler.is_active(
                self.active_simulation_tab
            )
        ):
            self.cleanup_active_simulation()

    def _simulation_view_menu(self, schema: SettingsSchema):
        simulation_tab = self.menu_system.new_tab(
            TabStyles.TWO_CONTAINERS,
            None,
        )

        frame = Frame(
            relative_position=(0, 0),
            height=400,
            accent_color=lambda: self.menu_system.color_scheme.accent(Accents.PINK),
        )
        frame.margin_after = 30
        metric_plot = Plot(
            relative_position=(0, 0),
            height=400,
            anchor=Position.CENTER, 
            dock=Position.CENTER
        )
        metric_plot.margin_after = 20
        setting_plot = Plot(
            relative_position=(0, 0),
            height=400,
            anchor=Position.CENTER,
            dock=Position.CENTER,
        )
        setting_plot.margin_after = 20


        simulation_tab.containers[0].add_child(frame, metric_plot, setting_plot)

        self.menu_system.add_settings_from_schema(
            simulation_tab.containers[1],
            schema=schema,
            include_all=False
        )
        self.menu_system.add_button_list(
            simulation_tab.containers[1],
            ("Back", lambda: self._close_sim(), Accents.PINK)
        )

        return simulation_tab, frame, metric_plot, setting_plot

    def _settings_menu(self, main_tab: Tab, settings: Settings):
        tab_handler = self.menu_system.tab_handler
        settings_tab = self.menu_system.new_tab(
            TabStyles.ONE_CONTAINER,
            "Settings",
            background=TabBackgrounds.HEX,
            accent=Accents.BLUE
        )

        self.menu_system.add_settings_from_schema(settings_tab.main_container, settings.expose_schema())
        self.menu_system.add_button_list(
            settings_tab.main_container,
            ("Back", lambda: tab_handler.reverse_shove(), Accents.PINK)
        )

        return settings_tab