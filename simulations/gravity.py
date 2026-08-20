import sympy as sp
from engine.simulation.engine import CentralForceSimulation
from engine.simulation.schema import SimulationSchema, SliderParam

class GravitySimulation(CentralForceSimulation):
    @classmethod
    def get_schema(cls):
        return SimulationSchema([
            SliderParam("u_G", "Gravitational Constant (G)", default=0.0000001, min_val=0.00000001, max_val=0.00001),
            SliderParam("particle_count", "Total Particles", default=1000, min_val=100, max_val=5000, is_int=True),
            SliderParam("mass_value", "Particle Mass", default=12.0, min_val=1.0, max_val=100.0)
        ])

    def __init__(self, ctx, config=None):
        super().__init__(ctx, config)
        p_count = int(self.config.get("particle_count", 1000))
        p_mass = float(self.config.get("mass_value", 12.0))

        dx, dy, dz, mass_j, r, u_G = sp.symbols("dx dy dz mass_j r u_G")
        ax = u_G * mass_j * dx / (r**3)
        ay = u_G * mass_j * dy / (r**3)
        az = u_G * mass_j * dz / (r**3)

        self.compile_physics_law(ax, ay, az)
        self.add_particles_cloud(count=p_count, mass_value=p_mass, charge_value=0.0)
        self.init_buffers()

    def update_uniforms(self):
        self.compute_program["u_G"] = float(self.config.get("u_G", 0.0000001))