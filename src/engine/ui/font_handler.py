"""
Font loading and caching for the UI system.
"""

from pathlib import Path

import pygame


def _find_project_root() -> Path:
    """Find the project root by searching for a project marker."""
    current = Path(__file__).resolve().parent

    while current != current.parent:
        if (current / "pyproject.toml").is_file():
            return current

        current = current.parent

    raise FileNotFoundError(
        "Could not find project root (no pyproject.toml found)."
    )


class FontHandler:
    """Loads and caches fonts from the project's assets/fonts directory."""

    _cache: dict[tuple[str, int], pygame.font.Font] = {}
    _project_root: Path | None = None

    DEFAULT_SIZE = 32

    @classmethod
    def _ensure_initialized(cls) -> None:
        """Ensure Pygame's font subsystem is initialized."""
        if not pygame.font.get_init():
            pygame.font.init()

    @classmethod
    def _get_project_root(cls) -> Path:
        """Return the project root, caching the result."""
        if cls._project_root is None:
            cls._project_root = _find_project_root()

        return cls._project_root

    @classmethod
    def load_font(
        cls,
        font_name: str,
        size: int = 16,
    ) -> pygame.font.Font:
        """Load and cache a font from assets/fonts/."""
        cls._ensure_initialized()

        key = (font_name, size)

        if key in cls._cache:
            return cls._cache[key]

        font_path = (
            cls._get_project_root()
            / "assets"
            / "fonts"
            / font_name
        )

        if not font_path.is_file():
            available = cls._list_available_fonts()

            raise FileNotFoundError(
                f"Font not found: {font_path}\n"
                f"Available fonts: {available}"
            )

        font = pygame.font.Font(str(font_path), size)
        cls._cache[key] = font

        return font

    @classmethod
    def default_font(cls) -> pygame.font.Font:
        """Return the default UI font."""
        cwd = Path(__file__).parent
        root = cwd.parent.parent.parent
        fontdir = root / "assets" / "fonts"
        return cls.load_font(fontdir / "Roboto-Regular.ttf", cls.DEFAULT_SIZE)
        # return cls.load_system_font(cls.DEFAULT_SIZE)

    @classmethod
    def load_system_font(
        cls,
        size: int = DEFAULT_SIZE,
    ) -> pygame.font.Font:
        """Load and cache Pygame's default system font."""
        cls._ensure_initialized()

        key = ("__default__", size)

        if key not in cls._cache:
            cls._cache[key] = pygame.font.Font(None, size)

        return cls._cache[key]

    @classmethod
    def _list_available_fonts(cls) -> list[str]:
        """Return the names of available font files."""
        fonts_dir = (
            cls._get_project_root()
            / "assets"
            / "fonts"
        )

        if not fonts_dir.is_dir():
            return []

        return [
            path.name
            for path in fonts_dir.iterdir()
            if path.is_file()
        ]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached fonts."""
        cls._cache.clear()