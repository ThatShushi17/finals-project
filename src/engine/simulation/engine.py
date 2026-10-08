import os
import vidmaker
import moderngl as mgl
import numpy as np
import sympy as sp
import pygame
import pandas as pd
from src.engine.shader_handler import load_shader
from .simulation import Simulation
from .schema import SimulationSchema

class CentralForceSimulation(Simulation):
    def __init__(self, ctx, config: dict = None):
        super().__init__(ctx, config)
        vert_src = load_shader('simulation/particle/render.vert')
        frag_src = load_shader('simulation/particle/render.frag')
        self.render_program = self.ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        self.raw_positions, self.raw_velocities, self.num_particles = [], [], 0
        self.pos_vbo, self.vel_buffer, self.energy_buffer, self.vao = None, None, None, None
        self.compute_program = None

        # --- Callback, State Tracking & History ---
        self.export_callback = self.config.get("export_callback", None)
        self.export_interval = self.config.get("export_interval", 10)
        self.step_counter = 0
        self.energy_history = []

        # Video Recorder Setup (respects configured FPS)
        self.is_recording = self.config.get("record_video", False)
        self.sim_fps = int(self.config.get("fps", 60))
        self.video = None

        if self.is_recording:
            os.makedirs("recordings", exist_ok=True)
            
            raw_filename = self.config.get("video_filename", "simulation_recording").strip()
            if not raw_filename:
                raw_filename = "simulation_recording"
            if not raw_filename.lower().endswith(".mp4"):
                raw_filename += ".mp4"
                
            filepath = os.path.join("recordings", raw_filename)
            
            self.video = vidmaker.Video(
                path=filepath, 
                fps=self.sim_fps, 
                resolution=(700, 450)
            )

    @classmethod
    def get_schema(cls) -> SimulationSchema:
        return SimulationSchema([])

    def compile_physics_law(self, ax_expr, ay_expr, az_expr):
        ax_code = sp.ccode(ax_expr)
        ay_code = sp.ccode(ay_expr)
        az_code = sp.ccode(az_expr)

        compute_template = load_shader('simulation/compute/gravity.comp')
        final_compute_src = compute_template.format(
            ax_expr=ax_code,
            ay_expr=ay_code,
            az_expr=az_code
        )
        self.compute_program = self.ctx.compute_shader(final_compute_src)

    def add_particles_cloud(self, count, mass_value=1.0, charge_value=0.0):
        phi = np.random.uniform(0, 2 * np.pi, count)
        costheta = np.random.uniform(-1, 1, count)
        u = np.random.uniform(0, 1, count)
        theta = np.arccos(costheta)
        r = 1.2 * np.cbrt(u)
        
        x = r * np.sin(theta) * np.cos(phi)
        y = r * np.sin(theta) * np.sin(phi)
        z = r * np.cos(theta)
        
        pos_data = np.stack((x, y, z, np.full(count, mass_value)), axis=1).astype('f4')
        vel_data = np.stack((-y * 0.003, x * 0.003, np.zeros(count), np.full(count, charge_value)), axis=1).astype('f4')
        
        self.raw_positions.extend(pos_data)
        self.raw_velocities.extend(vel_data)
        self.num_particles = len(self.raw_positions)

    def update_uniforms(self):
        pass

    def init_buffers(self):
        if self.num_particles == 0: return
        self.pos_vbo = self.ctx.buffer(np.array(self.raw_positions, dtype='f4').tobytes())
        self.vel_buffer = self.ctx.buffer(np.array(self.raw_velocities, dtype='f4').tobytes())
        
        padded_particles = int(np.ceil(self.num_particles / 128)) * 128
        self.energy_buffer = self.ctx.buffer(reserve=padded_particles * 8)
        
        self.vao = self.ctx.vertex_array(self.render_program, [(self.pos_vbo, '4f', 'in_pos_mass')])

    def export_state(self):
        if not hasattr(self, 'energy_history') or self.energy_history is None:
            self.energy_history = []

        if not self.energy_buffer or self.num_particles == 0: 
            return

        raw_energy_data = self.energy_buffer.read()
        energy_array = np.frombuffer(raw_energy_data, dtype='f4').reshape((-1, 2))
        
        valid_energy = energy_array[:self.num_particles]
        
        ke = float(np.sum(valid_energy[:, 0]))
        pe = float(np.sum(valid_energy[:, 1]))
        
        state_vars = {
            "step": self.step_counter,
            "kinetic_energy": ke,
            "potential_energy": pe,
            "total_energy": ke + pe
        }
        
        self.energy_history.append(state_vars)
        
        if self.export_callback:
            try:
                self.export_callback(state_vars)
            except Exception as e:
                print(f"Callback error: {e}")
                self.export_callback = None

    def step(self, dt):
        if not self.compute_program or self.num_particles == 0: return
        self.update_uniforms()
        grid_size_x = int(np.ceil(self.num_particles / 128))
        self.compute_program["u_num_particles"] = self.num_particles
        
        self.pos_vbo.bind_to_storage_buffer(binding=0)
        self.vel_buffer.bind_to_storage_buffer(binding=1)
        if self.energy_buffer:
            self.energy_buffer.bind_to_storage_buffer(binding=2)
            
        self.compute_program.run(group_x=grid_size_x)

        if self.export_callback and self.export_interval > 0:
            if self.step_counter % self.export_interval == 0:
                self.export_state()

        self.step_counter += 1

    def record_frame(self, frame_rect=(0, 0, 700, 450)):
        if not self.video: return
        
        frame_x, frame_y, width, height = frame_rect
        win_w, win_h = self.ctx.screen.size  
        
        gl_x = frame_x
        gl_y = win_h - frame_y - height
        
        raw_bytes = self.ctx.screen.read(viewport=(gl_x, gl_y, width, height), components=3)
        frame = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((height, width, 3))
        frame = np.ascontiguousarray(frame[::-1, :, ::-1])
        
        self.video.update(frame)

    def draw_simulation(self, view_proj, frame_rect=(0, 0, 700, 450)):
        if not self.vao: return
        self.render_program["u_view_proj"].write(view_proj)
        self.vao.render(mgl.POINTS)
        
        if self.is_recording:
            self.record_frame(frame_rect)
        
    def cleanup(self):
        super().cleanup()
        
        if not hasattr(self, 'energy_history') or self.energy_history is None:
            self.energy_history = []
            
        if self.energy_buffer and self.num_particles > 0:
            self.export_state()
        
        if self.energy_history:
            os.makedirs("readings", exist_ok=True)
            raw_filename = self.config.get("video_filename", "simulation_recording").strip()
            if not raw_filename:
                raw_filename = "simulation_recording"
            base_name = os.path.splitext(raw_filename)[0]
            csv_filepath = os.path.join("readings", f"{base_name}.csv")
            
            df = pd.DataFrame(self.energy_history)
            df.to_csv(csv_filepath, index=False)
            print(f"Energy log saved to {csv_filepath}")

        if self.video:
            self.video.export()
            self.video = None
        if self.pos_vbo: self.pos_vbo.release()
        if self.vel_buffer: self.vel_buffer.release()
        if self.energy_buffer: self.energy_buffer.release()
        if self.vao: self.vao.release()