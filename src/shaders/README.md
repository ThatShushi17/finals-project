# Shader Organization

## Overview
All inline GLSL shader code has been extracted from Python files and organized in the `shaders/` directory.

## Directory Structure

```
shaders/
├── ui/                            # UI rendering shaders
│   ├── frag.frag                  # UI fragment shader
│   └── vert.vert                  # UI vertex shader
│
└── simulation/                    # Physics simulation shaders
    ├── particle/                  # Particle rendering
    │   ├── render.vert            # Vertex shader (positions → screen)
    │   └── render.frag            # Fragment shader (particle colors)
    │
    └── compute/                   # GPU compute shaders
        └── gravity.comp           # Template for SymPy-injected physics
```

## Loading Shaders

### In Python Code

```python
from engine.shader_handler import load_shader

# Load single shader
vertex_code = load_shader('simulation/particle/render.vert')

# Load pair
vert, frag = load_shader_pair('simulation/particle/render.vert', 
                               'simulation/particle/render.frag')
```

### Location Resolution

Paths are resolved relative to `shaders/` directory automatically:
- `'simulation/particle/render.vert'` → `shaders/simulation/particle/render.vert`
- `'ui/vert.vert'` → `shaders/ui/vert.vert`

## Shader Files

### render.vert / render.frag
**Purpose:** Render particle positions as colored points in 3D space

**Inputs:**
- `in_pos_mass` — Position (x,y,z) and mass packed in vec4
- `u_view_proj` — Camera matrix

**Outputs:**
- Fragment color based on particle mass (blue for low mass, pink for high mass)
- Point size scales with depth for perspective effect

### gravity.comp
**Purpose:** Fixed gravity physics simulation

**Algorithm:**
- All-pairs force calculation (O(n²) per timestep)
- N-body gravity with softening parameter
- Box boundary conditions with bounce

**Uniforms:**
- `u_num_particles` — Particle count
- `u_G` — Gravitational constant (configurable)

### gravity.comp
**Purpose:** Template for student-defined physics laws via SymPy

**Template Variables:** `{ax_expr}`, `{ay_expr}`, `{az_expr}`

When used with `StudentSimulationSpace.compile_physics_law()`:
1. Student provides SymPy symbolic expressions
2. SymPy converts to GLSL C code
3. Code injected into template placeholders
4. Compiled as compute shader

**Example:**
```python
# Student code
fx = (G * mass_j * dx) / r**2.5
fy = (G * mass_j * dy) / r**2.5
fz = (G * mass_j * dz) / r**2.5

sim.compile_physics_law(fx, fy, fz)
# ↓ Generates acceleration code
# float ax = G*mass_j*dx/pow(r, 2.5);
# float ay = G*mass_j*dy/pow(r, 2.5);
# float az = G*mass_j*dz/pow(r, 2.5);
```

## Adding New Shaders

1. Create file in appropriate `shaders/simulation/` subdirectory
2. Use `load_shader()` in Python code
3. Relative path: `'simulation/category/shader_name.ext'`

### Naming Conventions

- **Compute:** `*.comp` (e.g., `coulomb.comp`, `drag.comp`)
- **Vertex:** `*.vert`
- **Fragment:** `*.frag`
- **Templates:** `*_template.comp`

## Benefits

- **Separation of concerns** — Shaders live in shader files, not Python strings  
- **Easy editing** — Syntax highlighting in any text editor  
- **Version control** — Easier to diff shader changes  
- **Code reusability** — Shaders can be shared across simulations  
- **Cleaner Python** — Logic code isn't cluttered with massive strings  
