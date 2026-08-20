import pygame
import os
import importlib.util
import pandas as pd
from .components import Tab, Container, Axis, Position, Label, Button, Slider, Checkbox, TextInput, Frame, MatplotlibComponent
from .font_handler import FontHandler
from .menu_system import MenuSystem
from ..simulation.simulation import Simulation
from ..simulation.schema import SliderParam, CheckboxParam, TextParam

class UIBuilder:
    def __init__(self, menu_system: MenuSystem, ctx):
        self.menu_system = menu_system
        self.ctx = ctx
        self.frame = None
        self.energy_plot = None
        
        self.target_fps = 60
        
        self.time_data = []
        self.ke_data = []
        self.pe_data = []
        self.te_data = []

        self.simulation_tab = self._simulation_view_menu()

    def create_ui(self, exit_callback):
        tab_handler = self.menu_system.tab_handler
        main_tab = Tab(tab_handler)

        settings_tab = self._settings_menu()
        select_simulation_tab = self._select_simulation_menu()
        view_graphs_tab = self._view_graphs_menu()

        main_container = Container(Axis.VERTICAL, cross_percent=0.8)
        
        title_label = Label((0, 0), "Physics Demo", (255, 255, 255), FontHandler.load_font("Roboto-Regular.ttf", 40))
        select_button = Button((0, 0), (200, 80), "Select Simulation", lambda *args, **kwargs: tab_handler.push(select_simulation_tab))
        graphs_button = Button((0, 0), (200, 80), "View Graphs", lambda *args, **kwargs: tab_handler.push(self._view_graphs_menu()))
        settings_button = Button((0, 0), (200, 80), "Settings", lambda *args, **kwargs: tab_handler.push(settings_tab))
        exit_button = Button((0, 0), (200, 80), "Exit App", exit_callback)
    
        main_container.add_child(title_label, select_button, graphs_button, settings_button, exit_button)
        main_container.define_margins(40, 30, 30, 30, 0)
        main_tab.add_child(main_container)

        tab_handler.push(main_tab)

    def _select_simulation_menu(self):
        tab_handler = self.menu_system.tab_handler
        select_simulation_tab = Tab(tab_handler)
        select_container = Container(Axis.VERTICAL, cross_percent=0.8)
        
        font_title = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 32)
        font_label = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 16)

        tab_name_label = Label((0, 0), "Choose Simulation", (255, 255, 255), font_title)
        select_container.add_child(tab_name_label)
        margins = [50]

        sim_dir = "simulations"
        if os.path.exists(sim_dir):
            files = [f for f in os.listdir(sim_dir) if f.endswith(".py")]
            for f in files:
                filepath = os.path.join(sim_dir, f)
                btn = Button((0, 0), (300, 50), f, lambda f=filepath: self._open_simulation_config(f), font=font_label)
                select_container.add_child(btn)
                margins.append(10)

        back_button = Button((0, 0), (120, 40), "Back", lambda *args, **kwargs: tab_handler.pop(), font=font_label)
        select_container.add_child(back_button)
        margins.append(50)

        select_container.define_margins(*margins)
        select_simulation_tab.add_child(select_container)

        return select_simulation_tab

    def _view_graphs_menu(self):
        tab_handler = self.menu_system.tab_handler
        graphs_tab = Tab(tab_handler)
        graphs_container = Container(Axis.VERTICAL, cross_percent=0.8)
        
        font_title = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 32)
        font_label = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 16)

        title_label = Label((0, 0), "Saved Readings", (255, 255, 255), font_title)
        graphs_container.add_child(title_label)
        margins = [40]

        readings_dir = "readings"
        if os.path.exists(readings_dir):
            csv_files = [f for f in os.listdir(readings_dir) if f.endswith(".csv")]
            if csv_files:
                for f in csv_files:
                    filepath = os.path.join(readings_dir, f)
                    btn = Button((0, 0), (320, 50), f, lambda path=filepath, filename=f: self._open_graph_detail(path, filename), font=font_label)
                    graphs_container.add_child(btn)
                    margins.append(10)
            else:
                empty_lbl = Label((0, 0), "No CSV logs found in readings/", (200, 200, 200), font_label)
                graphs_container.add_child(empty_lbl)
                margins.append(20)
        else:
            empty_lbl = Label((0, 0), "readings/ directory not found", (200, 200, 200), font_label)
            graphs_container.add_child(empty_lbl)
            margins.append(20)

        back_button = Button((0, 0), (120, 40), "Back", lambda *args, **kwargs: tab_handler.pop(), font=font_label)
        graphs_container.add_child(back_button)
        margins.append(40)

        graphs_container.define_margins(*margins)
        graphs_tab.add_child(graphs_container)
        return graphs_tab

    def _open_graph_detail(self, csv_filepath, filename):
        tab_handler = self.menu_system.tab_handler
        detail_tab = Tab(tab_handler)
        detail_container = Container(Axis.VERTICAL, cross_percent=0.9)
        font_label = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 16)

        title_label = Label((0, 0), f"Log: {filename}", (255, 255, 255), pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 24))
        
        plot_comp = MatplotlibComponent(
            rel_pos=(0, 0), 
            size=(700, 420), 
            anchor=Position.CENTER, 
            dock=Position.CENTER
        )

        if os.path.exists(csv_filepath):
            try:
                df = pd.read_csv(csv_filepath)
                steps = df["step"].values if "step" in df.columns else range(len(df))
                ke = df["kinetic_energy"].values if "kinetic_energy" in df.columns else []
                pe = df["potential_energy"].values if "potential_energy" in df.columns else []
                te = df["total_energy"].values if "total_energy" in df.columns else []
                
                plot_comp.ax.clear()
                if len(ke) > 0:
                    plot_comp.ax.plot(steps, ke, label="Kinetic (K)", color="red")
                if len(pe) > 0:
                    plot_comp.ax.plot(steps, pe, label="Potential (U)", color="blue")
                if len(te) > 0:
                    plot_comp.ax.plot(steps, te, label="Total (E)", color="green", linestyle='--')
                
                plot_comp.ax.legend(loc="upper right", fontsize=8)
                plot_comp.ax.set_title(f"Energy History: {filename}", fontsize=10)
                plot_comp.ax.set_xlabel("Step", fontsize=8)
                plot_comp.ax.set_ylabel("Energy", fontsize=8)
                plot_comp.fig.tight_layout()
                plot_comp.redraw()
            except Exception as e:
                print(f"Error loading CSV graph {csv_filepath}: {e}")

        back_button = Button((0, 0), (120, 40), "Back", lambda *args, **kwargs: tab_handler.pop(), font=font_label)
        
        detail_container.add_child(title_label, plot_comp, back_button)
        detail_container.define_margins(20, 20, 0)
        detail_tab.add_child(detail_container)

        tab_handler.push(detail_tab)

    def _open_simulation_config(self, filepath):
        config_tab = Tab(self.menu_system.tab_handler)
        config_container = Container(Axis.VERTICAL, cross_percent=0.8)

        font_title = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 32)
        font_label = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 16)

        title_label = Label((0, 0), f"Configure: {os.path.basename(filepath)}", (255, 255, 255), font_title)
        config_container.add_child(title_label)

        spec = importlib.util.spec_from_file_location("sim_module", filepath)
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
        config_state = schema.get_defaults()

        for param in schema.parameters:
            name = param.name
            label_text = param.label

            if isinstance(param, SliderParam):
                fmt = ".0f" if param.is_int else ".4f"
                lbl = Label((0, 0), lambda n=name, l=label_text, f=fmt: f"{l}: {config_state[n]:{f}}", (200, 200, 200), font_label)
                comp = Slider((0, 0), 200, config_state[name], (param.min_val, param.max_val), 
                              on_change=lambda val, n=name: config_state.update({n: val}))
                config_container.add_child(lbl, comp)
                
            elif isinstance(param, CheckboxParam):
                lbl = Label((0, 0), lambda n=name, l=label_text: f"{l}: {config_state[n]}", (200, 200, 200), font_label)
                comp = Checkbox((0, 0), (20, 20), initial_value=config_state[name], 
                                on_change=lambda val, n=name: config_state.update({n: val}))
                config_container.add_child(lbl, comp)
                
            elif isinstance(param, TextParam):
                lbl = Label((0, 0), lambda n=name, l=label_text: f"{l}:", (200, 200, 200), font_label)
                comp = TextInput((0, 0), (200, 30), initial_text=str(config_state[name]), 
                                 on_change=lambda val, n=name: config_state.update({n: val}))
                config_container.add_child(lbl, comp)

        config_state["record_video"] = False
        config_state["video_filename"] = "simulation_recording"

        record_lbl = Label((0, 0), lambda: f"Record Video: {config_state['record_video']}", (200, 200, 200), font_label)
        record_checkbox = Checkbox(
            (0, 0), 
            (20, 20), 
            initial_value=config_state["record_video"], 
            on_change=lambda val: config_state.update({"record_video": val})
        )
        config_container.add_child(record_lbl, record_checkbox)

        filename_lbl = Label((0, 0), "File Name:", (200, 200, 200), font_label)
        filename_input = TextInput(
            (0, 0),
            (200, 30),
            initial_text=config_state["video_filename"],
            on_change=lambda val: config_state.update({"video_filename": val})
        )
        config_container.add_child(filename_lbl, filename_input)

        # Inject global target FPS into config state
        config_state["fps"] = self.target_fps

        launch_btn = Button((0, 0), (200, 50), "Create Simulation", 
                            lambda *args, **kwargs: self._launch_simulation(sim_class, config_state), 
                            font=font_label)
        back_btn = Button((0, 0), (120, 40), "Back", 
                          lambda *args, **kwargs: self.menu_system.tab_handler.pop(), 
                          font=font_label)

        config_container.add_child(launch_btn, back_btn)
        
        num_children = len(config_container.children)
        margins = [10] * num_children
        margins[0] = 30
        margins[-3] = 40
        config_container.define_margins(*margins)

        config_tab.add_child(config_container)
        self.menu_system.tab_handler.push(config_tab)

    def _on_sim_state_update(self, state):
        self.time_data.append(state.get("step", 0))
        self.ke_data.append(state.get("kinetic_energy", 0))
        self.pe_data.append(state.get("potential_energy", 0))
        self.te_data.append(state.get("total_energy", 0))

        if len(self.time_data) > 100:
            self.time_data.pop(0)
            self.ke_data.pop(0)
            self.pe_data.pop(0)
            self.te_data.pop(0)

        self.energy_plot.ax.clear()
        self.energy_plot.ax.plot(self.time_data, self.ke_data, label="Kinetic (K)", color="red")
        self.energy_plot.ax.plot(self.time_data, self.pe_data, label="Potential (U)", color="blue")
        self.energy_plot.ax.plot(self.time_data, self.te_data, label="Total (E)", color="green", linestyle='--')
        
        self.energy_plot.ax.legend(loc="upper right", fontsize=8)
        self.energy_plot.ax.set_title("System Energy over Time", fontsize=10)
        self.energy_plot.fig.tight_layout()
        self.energy_plot.redraw()

    def _launch_simulation(self, sim_class, config_state):
        if self.frame.simulation:
            self.frame.simulation.cleanup()

        self.time_data.clear()
        self.ke_data.clear()
        self.pe_data.clear()
        self.te_data.clear()
        self.energy_plot.ax.clear()
        self.energy_plot.redraw()

        config_state["fps"] = self.target_fps
        config_state["export_callback"] = self._on_sim_state_update
        config_state["export_interval"] = 10 

        self.frame.simulation = sim_class(self.ctx, config=config_state)
        
        self.menu_system.tab_handler.pop() 
        self.menu_system.tab_handler.push(self.simulation_tab)

    def _close_sim(self, tab):
        if self.frame.simulation:
            self.frame.simulation.cleanup()
            self.frame.simulation = None
            
        self.energy_plot.ax.clear()
        self.energy_plot.redraw()
        
        tab.handler.pop()

    def _simulation_view_menu(self):
        simulation_tab = Tab(self.menu_system.tab_handler)
        sim_container = Container(Axis.VERTICAL, cross_percent=0.9)
        font_label = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 16)
        
        self.frame = Frame((0, 0), (700, 400))
        
        self.energy_plot = MatplotlibComponent(
            rel_pos=(0, 0), 
            size=(700, 200),  
            anchor=Position.CENTER, 
            dock=Position.CENTER
        )
        
        back_button = Button((0, 0), (120, 40), "Back", lambda *args, **kwargs: self._close_sim(simulation_tab), font=font_label)
        
        sim_container.add_child(self.frame, self.energy_plot, back_button)
        sim_container.define_margins(-50, -50, 0)
        simulation_tab.add_child(sim_container)

        return simulation_tab

    def _settings_menu(self):
        tab_handler = self.menu_system.tab_handler
        settings_tab = Tab(tab_handler)
        settings_container = Container(Axis.VERTICAL, cross_percent=0.8)
        font_title = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 32)
        font_label = pygame.font.Font("assets/fonts/Roboto-Regular.ttf", 16)

        title_label = Label((0, 0), "Settings", (255, 255, 255), font_title)
        
        fps_lbl = Label((0, 0), lambda: f"Simulation FPS: {int(self.target_fps)}", (200, 200, 200), font_label)
        fps_slider = Slider((0, 0), 200, self.target_fps, (15, 144), 
                            on_change=lambda val: setattr(self, 'target_fps', int(val)))

        back_button = Button((0, 0), (120, 40), "Back", lambda *args, **kwargs: tab_handler.pop(), font=font_label)

        settings_container.add_child(title_label, fps_lbl, fps_slider, back_button)
        settings_container.define_margins(40, 30, 20, 40)
        settings_tab.add_child(settings_container)
        return settings_tab