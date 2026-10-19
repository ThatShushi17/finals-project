from pathlib import Path

import pygame

def _find_root():
    cwd = Path(__file__).resolve().parent

    while cwd != cwd.parent:
        if (cwd / "pyproject.toml").is_file():
            return cwd

        cwd = cwd.parent

    raise FileNotFoundError("Could not find pyproject.toml at project root.")

class FontHandler:
    font_dir = _find_root() / "assets" / "fonts"

    def __init__(
        self,
        default_font: Path,  # TODO: sidequest, Callable[[], Path] then add to Settings
        default_bold: Path,
        default_size: int
    ) -> None:
        self.default_font = default_font
        self.default_bold = default_bold
        self.default_size = default_size

        self._font_paths: dict[str, Path] = {}
        self._cache: dict[tuple[str, int], pygame.font.Font] = {}
        
        self.load_font(default_font, default_size)
        self.load_font(default_bold, default_size)

    def get_bold(self, size: int | None = None):
        return self.get_font(self.default_bold, size if size is not None else self.default_size)

    def get_heading(self):
        return self.get_bold(int(self.default_size * 1.8))

    def get_font(self, font: str | Path | None = None, size: int | None = None) -> pygame.font.Font:
        size = size if size is not None else self.default_size
        font = font if font is not None else self.default_font

        label = font if isinstance(font, str) else font.stem
        
        if (label, size) in self._cache:
            return self._cache[label, size]
        
        elif isinstance(font, Path):
            try:
                return self.load_font(font, size)
            except (FileNotFoundError, OSError, pygame.error):
                if font == self.default_font:
                    f = pygame.font.Font(None, size)
                    if ("__TRUE_DEFAULT", size) not in self._cache:
                        self._cache[("__TRUE_DEFAULT", size)] = f
                    return f
                else:
                    return self.get_font(self.default_font, size)
        elif label in self._font_paths:
            return self.load_font(
                self._font_paths[label],
                size
            )
        else:
            return self.get_font(size=size)

    def load_font(self, font_path: Path, size: int) -> pygame.font.Font:
        if not font_path.is_file():
            raise FileNotFoundError(f"font at {str(font_path)} not found.")

        label = str(font_path.stem)
        font = pygame.font.Font(str(font_path), size)
        self._cache[(label, size)] = font
        if label not in self._font_paths:
            self._font_paths[label] = font_path
        return font
