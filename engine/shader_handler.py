"""Utility for loading shader files from disk."""

from pathlib import Path


def _find_project_root() -> Path:
    """Find the project root by looking for pyproject.toml or main.py."""
    current = Path(__file__).resolve().parent
    
    while current != current.parent:  # Stop at filesystem root
        # Check for project markers
        if (current / "pyproject.toml").exists() or (current / "main.py").exists():
            return current
        current = current.parent
    
    raise FileNotFoundError("Could not find project root (looking for pyproject.toml or main.py)")


def load_shader(shader_name: str) -> str:
    """
    Load a shader file from shaders/ directory.
    
    Args:
        shader_name: Path relative to shaders/ (e.g., 'simulation/particle/render.vert')
    
    Returns:
        Shader source code as string
    
    Raises:
        FileNotFoundError: If shader file doesn't exist
    """
    project_root = _find_project_root()
    shader_path = project_root / "shaders" / shader_name
    
    if not shader_path.exists():
        raise FileNotFoundError(f"Shader not found: {shader_path}")
    
    with open(shader_path, "r") as f:
        return f.read()


def load_shader_pair(vertex_path: str, fragment_path: str) -> tuple[str, str]:
    """
    Load vertex and fragment shader pair.
    
    Args:
        vertex_path: Path to vertex shader (relative to shaders/)
        fragment_path: Path to fragment shader (relative to shaders/)
    
    Returns:
        Tuple of (vertex_source, fragment_source)
    """
    return load_shader(vertex_path), load_shader(fragment_path)
