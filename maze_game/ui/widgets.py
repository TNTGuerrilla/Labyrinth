"""Shared colors, fonts and drawing helpers for the game's pygame UI."""
from __future__ import annotations

from typing import Any, Optional

import pygame

TEXT = (225, 228, 235)
MUTED = (150, 154, 165)
WARN = (240, 190, 90)
BAR_BG = (14, 15, 19)
PANEL = (22, 23, 28)
BUTTON = (38, 40, 48)
HOVER = (54, 58, 70)
ACTIVE = (40, 90, 160)
BORDER = (80, 84, 96)
HILITE = (44, 50, 66)
FONT_NAME = "segoeui"  # SysFont falls back to pygame's default font if missing

_fonts: dict[int, pygame.font.Font] = {}


def font(size: int) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
        _fonts.clear()

    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont(FONT_NAME, size)
    else:
        # Verify cached font is still valid
        try:
            _fonts[size].get_height()
        except pygame.error:
            # Font became invalid after pygame.quit(), recreate it
            _fonts[size] = pygame.font.SysFont(FONT_NAME, size)

    return _fonts[size]


def format_time(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def text(surface: pygame.Surface, s: str, pos: tuple[int, int], size: int = 16,
         color: tuple = TEXT, anchor: str = "topleft") -> pygame.Rect:
    image = font(size).render(s, True, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def button_rect(label: str, pos: tuple[int, int], size: int = 16, anchor: str = "topleft",
                pad: int = 10, height: int = 28) -> pygame.Rect:
    rect = pygame.Rect(0, 0, font(size).size(label)[0] + 2 * pad, height)
    setattr(rect, anchor, pos)
    return rect


def draw_button(surface: pygame.Surface, rect: pygame.Rect, label: str, size: int = 16,
                active: bool = False, hovered: bool = False) -> None:
    color = ACTIVE if active else HOVER if hovered else BUTTON
    pygame.draw.rect(surface, color, rect, border_radius=5)
    pygame.draw.rect(surface, BORDER, rect, 1, border_radius=5)
    text(surface, label, rect.center, size, anchor="center")


def draw_split_button(surface: pygame.Surface, main: pygame.Rect,
                      close: Optional[pygame.Rect], label: str, hover_main: bool,
                      hover_close: bool, size: int = 15) -> None:
    """One rounded control in two parts with a thin divider: `main` on the left and, when
    given, `close` (an x) on the right. Only the hovered part changes color."""
    radius = 5
    main_color = HOVER if hover_main else ACTIVE
    if close is None:
        pygame.draw.rect(surface, main_color, main, border_radius=radius)
        outline = main
    else:
        pygame.draw.rect(surface, main_color, main, border_top_left_radius=radius,
                         border_bottom_left_radius=radius)
        pygame.draw.rect(surface, HOVER if hover_close else ACTIVE, close,
                         border_top_right_radius=radius, border_bottom_right_radius=radius)
        pygame.draw.line(surface, BORDER, (close.x, close.y + 5), (close.x, close.bottom - 6))
        outline = main.union(close)
    pygame.draw.rect(surface, BORDER, outline, 1, border_radius=radius)
    text(surface, label, main.center, size, anchor="center")
    if close is not None:
        text(surface, "x", close.center, size, anchor="center")


def dim(surface: pygame.Surface) -> None:
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 150))
    surface.blit(shade, (0, 0))


def draw_panel(surface: pygame.Surface, rect: pygame.Rect) -> None:
    pygame.draw.rect(surface, PANEL, rect, border_radius=8)
    pygame.draw.rect(surface, BORDER, rect, 1, border_radius=8)


def draw_progress(surface: pygame.Surface, area: pygame.Rect, label: str,
                  fraction: float) -> None:
    box = pygame.Rect(0, 0, min(520, area.w - 32), 100)
    box.center = area.center
    draw_panel(surface, box)
    text(surface, label, (box.centerx, box.y + 26), 16, anchor="center")
    bar = pygame.Rect(box.x + 20, box.y + 50, box.w - 40, 14)
    pygame.draw.rect(surface, BUTTON, bar, border_radius=4)
    filled = round(bar.w * max(0.0, min(1.0, fraction)))
    if filled:
        pygame.draw.rect(surface, ACTIVE, (bar.x, bar.y, filled, bar.h), border_radius=4)
    text(surface, "Esc cancels", (box.centerx, box.bottom - 16), 13, MUTED, anchor="center")


class Hits:
    """Clickable rectangles recorded while drawing; the first match wins."""

    def __init__(self):
        self._items: list[tuple[pygame.Rect, Any]] = []

    def clear(self) -> None:
        self._items.clear()

    def add(self, rect: pygame.Rect, value: Any) -> None:
        self._items.append((pygame.Rect(rect), value))

    def at(self, pos: tuple[int, int]) -> Optional[Any]:
        for rect, value in self._items:
            if rect.collidepoint(pos):
                return value
        return None

    def rect_for(self, value: Any) -> Optional[pygame.Rect]:
        for rect, v in self._items:
            if v == value:
                return rect
        return None
