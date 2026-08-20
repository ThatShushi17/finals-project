"""
Font loader for UI system with robust project root detection.
Caches fonts to avoid repeated loading.
"""

import pygame
from pathlib import Path
from typing import Dict, Optional


def _find_project_root() -> Path:
	"""
	Search for project root by looking for pyproject.toml or main.py markers.
	Walks up directory tree until finding a marker file.
	"""
	current = Path(__file__).resolve()
	
	while current != current.parent:
		if (current / "pyproject.toml").exists() or (current / "main.py").exists():
			return current
		current = current.parent
	
	raise FileNotFoundError(
		"Could not find project root. Looked for pyproject.toml or main.py in parent directories."
	)


class FontHandler:
	"""Manages font loading with caching."""
	
	_cache: Dict[tuple, pygame.font.Font] = {}
	_project_root: Optional[Path] = None
	
	@classmethod
	def _get_project_root(cls) -> Path:
		"""Lazy-load project root once."""
		if cls._project_root is None:
			cls._project_root = _find_project_root()
		return cls._project_root
	
	@classmethod
	def load_font(cls, font_name: str, size: int = 16) -> pygame.font.Font:
		"""
		Load a font from assets/fonts/ directory.
		
		Args:
			font_name: Filename relative to assets/fonts/ (e.g., "Roboto-Regular.ttf")
			size: Font size in pixels (default: 16)
		
		Returns:
			pygame.font.Font object (cached for reuse)
		
		Raises:
			FileNotFoundError: If font file not found
		"""
		cache_key = (font_name, size)
		
		# Return cached font if available
		if cache_key in cls._cache:
			return cls._cache[cache_key]
		
		# Find and load font
		project_root = cls._get_project_root()
		font_path = project_root / "assets" / "fonts" / font_name
		
		if not font_path.exists():
			raise FileNotFoundError(
				f"Font not found: {font_path}\n"
				f"Looked in: {project_root / 'assets' / 'fonts'}\n"
				f"Available fonts: {cls._list_available_fonts()}"
			)
		
		font = pygame.font.Font(str(font_path), size)
		cls._cache[cache_key] = font
		return font
	
	@classmethod
	def _list_available_fonts(cls) -> list:
		"""List available fonts for error messages."""
		try:
			project_root = cls._get_project_root()
			fonts_dir = project_root / "assets" / "fonts"
			if fonts_dir.exists():
				return [f.name for f in fonts_dir.glob("*")]
		except:
			pass
		return []
	
	@classmethod
	def clear_cache(cls):
		"""Clear font cache (useful for testing)."""
		cls._cache.clear()
