import pygame

from ...settings import Settings
from ...enums import Accents

def _flip_hexstring(color: str):
    colors_part = color[1:]
    r, g, b = colors_part[0:2], colors_part[2:4], colors_part[4:6]
    return f"#{b}{g}{r}"

class ColorScheme:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.themes = settings.themes
        self._cached_theme: str | None = None
        self._color_cache: dict[str, pygame.Color] = {}

    def current_theme(self) -> str:
        return self.settings.theme.value

    def color(self, name: str) -> pygame.Color:
        theme = self.current_theme()
        if theme != self._cached_theme:
            self._cached_theme = theme
            self._color_cache.clear()
        if name not in self._color_cache:
            self._color_cache[name] = pygame.Color(
                _flip_hexstring(self.themes.loc[theme, name])  # type: ignore
            )
        return pygame.Color(self._color_cache[name])

    def accent(self, accent: Accents):
        return self.color("accent" + accent.value)

    def fg_bold(self):
        return self.color("secondary")

    def fg_hover(self):
        return self.color("secondary_bold")

    def fg(self):
        return self.color("secondary_dull")

    def bg(self):
        return self.color("primary")

    def bg_border(self):
        return self.color("primary_dark")
    
    def bg_bold(self):
        return self.color("primary_dull")