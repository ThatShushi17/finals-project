import pygame

from collections.abc import Callable

from ....types import Dual, Colorlike
from ....enums import Position

from ...frame_data import FrameData
from ..component import Component

def _resolve_color(color: Colorlike | Callable[[], Colorlike]) -> Colorlike:
    return color() if callable(color) else color


def _darken_color(color: Colorlike | Callable[[], Colorlike]) -> pygame.Color:
    resolved = pygame.Color(_resolve_color(color))
    return pygame.Color(
        round(resolved.r * 0.75),
        round(resolved.g * 0.75),
        round(resolved.b * 0.75),
        resolved.a,
    )


class Dropdown(Component):
    PADDING_X = 10
    PADDING_Y = 6
    ARROW_WIDTH = 20
    PLACEHOLDER_OPACITY = 0.4

    def __init__(
        self,
        relative_position: Dual,
        min_width: int,
        options: tuple[str, ...],
        placeholder_text: str,
        font: pygame.font.Font,
        color: Colorlike | Callable[[], Colorlike] = (255, 255, 255),
        background_color: Colorlike | Callable[[], Colorlike] = (30, 30, 30),
        border_color: Colorlike | Callable[[], Colorlike] = (100, 100, 100),
        accent_color: Colorlike | Callable[[], Colorlike] = (106, 73, 255),
        hover_color: Colorlike | Callable[[], Colorlike] | None = None,
        on_change: Callable[[str], None] = lambda _: None,
        anchor: Position = Position.CENTER,
        dock: Position = Position.CENTER,
        default_value: str | None = None,
    ):
        self.font = font
        self.options = options
        self.placeholder_text = placeholder_text

        self.color = color
        self.background_color = background_color
        self.border_color = border_color
        self.accent_color = accent_color
        self.hover_color = hover_color

        self.on_change = on_change
        self.value = default_value

        text_widths = [
            font.size(text)[0]
            for text in (*options, placeholder_text)
        ]
        width = max(
            min_width,
            max(text_widths, default=0)
            + 2 * self.PADDING_X
            + self.ARROW_WIDTH,
        )
        text_heights = [
            font.size(text)[1]
            for text in (*options, placeholder_text)
        ]
        self.option_height = (
            max(text_heights, default=font.get_linesize())
            + 2 * self.PADDING_Y
        )
        height = self.option_height
        self.min_width = min_width

        super().__init__(
            relative_position=relative_position,
            size=(width, height),
            anchor=anchor,
            dock=dock,
        )

        self.is_open = False
        self.is_hovered = False
        self.hovered_option: int | None = None
        self._text_surface_cache: dict[
            tuple[str, tuple[int, int, int, int], int | None],
            pygame.Surface,
        ] = {}

    def _update_size(self):
        text_widths = [
            self.font.size(text)[0]
            for text in (*self.options, self.placeholder_text)
        ]
        if self.value is not None:
            text_widths.append(self.font.size(self.value)[0])
        width = max(
            self.min_width,
            max(text_widths, default=0)
            + 2 * self.PADDING_X
            + self.ARROW_WIDTH,
        )
        self.size = (width, self.option_height)
        self.rect.size = self.size

    def _text_surface(
        self,
        text: str,
        color: Colorlike | Callable[[], Colorlike],
        alpha: int | None = None,
    ) -> pygame.Surface:
        resolved_color = pygame.Color(_resolve_color(color))
        color_key = (
            resolved_color.r,
            resolved_color.g,
            resolved_color.b,
            resolved_color.a,
        )
        key = (text, color_key, alpha)
        if key not in self._text_surface_cache:
            text_surface = self.font.render(text, True, resolved_color)
            if alpha is not None:
                text_surface.set_alpha(alpha)
            self._text_surface_cache[key] = text_surface
        return self._text_surface_cache[key]

    def _get_option_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(
            self.rect.left,
            self.rect.bottom + index * self.option_height,
            self.rect.width,
            self.option_height,
        )

    def _get_option_at(self, pos: Dual) -> int | None:
        if not self.is_open:
            return None

        for index in range(len(self.options)):
            if self._get_option_rect(index).collidepoint(pos):
                return index

        return None

    def _on_update(self, frame_data: FrameData):
        self.is_hovered = self.rect.collidepoint(frame_data.mouse_pos)

        for event in frame_data.events:
            if frame_data.is_event_consumed(event):
                continue
            if (event.type != pygame.MOUSEBUTTONUP or event.button != 1):
                continue

            pos = getattr(event, "pos", frame_data.mouse_pos)

            if self.rect.collidepoint(pos):
                self.is_open = not self.is_open and bool(self.options)
                frame_data.consume_event(event)

            elif self.is_open:
                index = self._get_option_at(pos)

                if index is not None:
                    selected = self.options[index]

                    if selected != self.value:
                        self.value = selected
                        self.on_change(selected)

                    frame_data.consume_event(event)
                self.is_open = False

        self.hovered_option = (
            self._get_option_at(frame_data.mouse_pos)
            if self.is_open
            else None
        )

    def draw(self, surf: pygame.Surface):
        dx, dy = self.offset
        draw_rect = self.rect.move(dx, dy)
        background_color = _resolve_color(self.background_color)

        pygame.draw.rect(surf, background_color, draw_rect)
        border_color = self.accent_color if self.is_hovered or self.is_open else self.border_color
        pygame.draw.rect(surf, _resolve_color(border_color), draw_rect, width=1)

        text = self.value if self.value is not None else self.placeholder_text
        
        text_surf = self._text_surface(
            text,
            self.color,
            round(255 * Dropdown.PLACEHOLDER_OPACITY)
            if self.value is None
            else None,
        )

        text_rect = text_surf.get_rect(midleft=(draw_rect.left + self.PADDING_X, draw_rect.centery))
        surf.blit(text_surf, text_rect)

        # dropdown indicator
        arrow_color = _resolve_color(self.color)
        arrow_x = draw_rect.right - self.PADDING_X - 5
        arrow_y = draw_rect.centery

        if self.is_open:
            arrow_points = [
                (arrow_x - 5, arrow_y + 2),
                (arrow_x + 5, arrow_y + 2),
                (arrow_x, arrow_y - 4),
            ]
        else:
            arrow_points = [
                (arrow_x - 5, arrow_y - 2),
                (arrow_x + 5, arrow_y - 2),
                (arrow_x, arrow_y + 4),
            ]

        pygame.draw.polygon(surf, arrow_color, arrow_points)

        super().draw(surf)
        self.draw_popup(surf)

    def draw_popup(self, surf: pygame.Surface) -> None:
        if not self.is_open or not self.options:
            return

        dx, dy = self.offset
        draw_rect = self.rect.move(dx, dy)
        menu_rect = pygame.Rect(
            draw_rect.left,
            draw_rect.bottom,
            draw_rect.width,
            len(self.options) * self.option_height,
        )
        previous_clip = surf.get_clip()
        surf.set_clip(previous_clip.union(menu_rect).clip(surf.get_rect()))
        try:
            background_color = _resolve_color(self.background_color)
            pygame.draw.rect(surf, background_color, menu_rect)
            option_hover_color = (
                self.hover_color
                if self.hover_color is not None
                else _darken_color(background_color)
            )

            for index, option in enumerate(self.options):
                option_rect = pygame.Rect(
                    draw_rect.left,
                    draw_rect.bottom + index * self.option_height,
                    draw_rect.width,
                    self.option_height,
                )
                if index == self.hovered_option:
                    pygame.draw.rect(
                        surf,
                        _resolve_color(option_hover_color),
                        option_rect,
                    )

                option_surf = self._text_surface(option, self.color)
                text_rect = option_surf.get_rect(
                    midleft=(
                        option_rect.left + self.PADDING_X,
                        option_rect.centery,
                    ),
                )
                surf.blit(option_surf, text_rect)

                if index < len(self.options) - 1:
                    pygame.draw.line(
                        surf,
                        _resolve_color(self.border_color),
                        (option_rect.left, option_rect.bottom),
                        (option_rect.right, option_rect.bottom),
                    )

            pygame.draw.rect(
                surf,
                _resolve_color(self.border_color),
                menu_rect,
                width=1,
            )
        finally:
            surf.set_clip(previous_clip)