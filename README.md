# Physics Simulation Framework

A student-friendly Python framework for building interactive physics simulations with GPU acceleration. No graphics programming experience required.

## Overview

This project provides a high-level API for creating particle-based physics simulations without diving into low-level graphics code. Students can:

- Define custom physics laws using symbolic math (SymPy)
- Combine pre-built forces (gravity, electrostatics, drag)
- Visualize simulations in real-time with an interactive UI
- Run GPU-accelerated computations (OpenGL compute shaders)

## Quick Start

### Installation

```bash
uv sync
```

### Run the Application

```bash
python main.py
```

This launches the interactive menu where you can select from available simulations.

### Run Tests

```bash
python tests.py
```

Verifies all dependencies (NumPy, PyGame, ModernGL, SymPy) are installed and working.

## Creating Your First Simulation

### Option 1: Use a Preset (Easiest)

```python
# simulations/my_gravity.py
from engine.simulation.presets import GravityPreset

def load_simulation(ctx):
    sim = GravityPreset(ctx, G=1e-5)
    sim.add_particle_cloud(count=1000, mass=0.01)
    sim.add_particle_cloud(count=500, mass=0.05)
    return sim
```

### Option 2: Define Custom Physics Laws

```python
# simulations/my_custom.py
import sympy as sp
from engine.simulation.engine import StudentSimulationSpace

def load_simulation(ctx):
    # Define symbolic variables
    dx, dy, dz, mass_j, r, u_G = sp.symbols('dx dy dz mass_j r u_G')
    
    # Write your physics equations
    acceleration_x = (u_G * mass_j * (dx / r)) / (r**2)
    acceleration_y = (u_G * mass_j * (dy / r)) / (r**2)
    acceleration_z = (u_G * mass_j * (dz / r)) / (r**2)
    
    # Create simulation
    sim = StudentSimulationSpace(ctx)
    sim.compile_physics_law(acceleration_x, acceleration_y, acceleration_z)
    sim.add_particles_cloud(count=2000, mass_value=1.0)
    sim.init_buffers()
    
    return sim
```

## Project Structure

```
finals-project/
├── main.py                 # Application entry point
├── tests.py               # Test runner
├── engine/
│   ├── simulation/
│   │   ├── engine.py      # StudentSimulationSpace (SymPy-based)
│   │   ├── logic.py       # SimulationSpace (fixed gravity)
│   │   └── shaders/       # GLSL compute shader templates
│   └── ui/
│       ├── core.py        # Base UI components
│       ├── menu_system.py # Tab navigation
│       └── components/    # Buttons, sliders, text inputs, etc.
├── simulations/           # Your simulation scripts go here
│   ├── gravity.py         # Example: Custom SymPy gravity
│   └── sim_grav.py        # Example: Preset gravity
├── tests/
│   ├── test_libs.py       # Environment verification
│   └── test_compute.py    # GPU compute shader tests
└── shaders/
    └── ui/                # UI rendering shaders
```

## API Reference

### StudentSimulationSpace

For students who want to define custom physics:

```python
from engine.simulation.engine import StudentSimulationSpace
import sympy as sp

sim = StudentSimulationSpace(ctx)

# Define forces using SymPy symbols
dx, dy, dz, mass_j, r, u_G = sp.symbols('dx dy dz mass_j r u_G')
fx = u_G * mass_j * (dx / r) / (r**2)
fy = u_G * mass_j * (dy / r) / (r**2)
fz = u_G * mass_j * (dz / r) / (r**2)

# Compile symbolic math to GPU compute shader
sim.compile_physics_law(fx, fy, fz)

# Add particles
sim.add_particles_cloud(count=1000, mass_value=0.01)
sim.init_buffers()

# Step simulation & render
sim.step(attraction_constant=1e-5)
sim.render(width, height)
```

### SimulationSpace

For fixed physics (no custom laws):

```python
from engine.simulation.logic import SimulationSpace

sim = SimulationSpace(width=800, height=600)
sim.add_particles(count=1000, mass_value=0.01)
sim.run(attraction_constant=0.00000005)
```

### Container Layout

Build UIs with flexbox-inspired layouts:

```python
from engine.ui import Container, Axis, Label, Button

# Vertical stack of components
container = Container(Axis.VERTICAL, cross_percent=0.8)
container.add_child(label, button1, button2)
container.define_margins(20, 10, 10)  # Spacing between children
```

## Architecture

### Simulation Pipeline

1. **Physics Definition** — Student defines forces (SymPy or preset)
2. **Compilation** — Symbolic math → GPU compute shader
3. **Compute** — GPU executes physics (parallel particle-particle forces)
4. **Render** — CPU reads back positions, GPU renders as points
5. **Display** — Rendered to texture, UI composited on top

### GPU Acceleration

- Uses **ModernGL** for OpenGL 4.3+ context
- **Compute shaders** run physics in parallel (128 threads per workgroup)
- **SSBO** (Shader Storage Buffer Objects) for position/velocity data
- No CPU-side physics calculations for large particle counts

## Learning Path

**Tier 1 (Zero Code):**
- Adjust parameters in presets
- Watch simulations

**Tier 2 (Equation Writing):**
- Write physics equations in SymPy
- See them compiled to GPU code

**Tier 3 (Force Composition):**
- Combine multiple forces
- Build complex emergent behavior

**Tier 4 (Visualization):**
- Custom particle colors (by velocity, mass, acceleration)
- Vector field visualization
- Particle trails

## Examples

### Gravity Simulation
```bash
python main.py
# Select "gravity.py" from menu
```

### Simple Gravity (Standalone)
```bash
python simulations/sim_grav.py
```

## Dependencies

- `moderngl>=5.12.0` — OpenGL context & GPU programming
- `pygame>=2.6.1` — Window management & input
- `numpy>=2.5.1` — Numerical arrays
- `pyglm>=2.8.3` — Vector/matrix math
- `sympy>=1.14.0` — Symbolic math & physics equations

## Troubleshooting

### "Failed to create OpenGL 4.3 context"
Your GPU or drivers don't support OpenGL 4.3. Update GPU drivers or use a machine with a more recent GPU.

### "Shader compilation failed"
Check that your SymPy expression is valid. Invalid expressions may not convert to valid GLSL. See `test_compute.py` for shader debugging.

### Simulation runs slowly
- Reduce particle count
- Reduce screen resolution
- Check GPU memory usage

## Testing

```bash
python tests.py
```

Tests:
- ✓ Environment setup (NumPy, Pandas, PyGame, ModernGL)
- ✓ OpenGL 4.3 context creation
- ✓ Compute shader compilation
- ✓ GPU compute execution with data validation

## Future Roadmap

- [ ] Coulomb force preset
- [ ] Flocking/boid preset
- [ ] Drag force preset
- [ ] Force composition API (`CompoundSimulation`)
- [ ] Visualization modes (velocity color, vector fields, trails)
- [ ] Performance profiling tools
- [ ] Particle collision detection

## Contributing

To add a new simulation:

1. Create `simulations/my_simulation.py`
2. Implement `load_simulation(ctx)` function
3. Return a `StudentSimulationSpace` or preset instance
4. Simulation appears in UI menu automatically

## License

Educational use only.

---

**Built for students who want to explore physics, not graphics APIs.**
