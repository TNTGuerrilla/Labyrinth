"""The dim "update available" line the screensaver shows on the primary monitor. It sits in
the margin the maze never uses (a board fills at most 80% of each side, see board.fill) and
moves to the next corner every few minutes so it cannot burn in."""
from __future__ import annotations

from typing import Optional, Sequence

import pygame

from .layout import Rect

CORNER_SECONDS = 180.0
COLOR = (95, 95, 95)
BLACK = (0, 0, 0)
FONT_NAME = "segoeui"  # SysFont falls back to pygame's default font if missing
CORNERS = ("bottomright", "bottomleft", "topleft", "topright")


def primary_index(boards: Sequence[Rect]) -> int:
    """Which board is on the primary monitor: Windows puts its top-left corner at (0, 0)."""
    return next((i for i, r in enumerate(boards) if r.x == 0 and r.y == 0), 0)


class Watermark:
    def __init__(self, message: str, size: tuple[int, int], started: float):
        if not pygame.font.get_init():
            pygame.font.init()
        w, h = size
        self.size = size
        self.started = started
        self.corner: Optional[int] = None  # the corner last drawn
        font = pygame.font.SysFont(FONT_NAME, max(12, min(w, h) // 54))
        image = font.render(message, True, COLOR)
        limit = w * 9 // 10
        if image.get_width() > limit:
            scale = limit / image.get_width()
            image = pygame.transform.smoothscale(
                image, (limit, max(1, round(image.get_height() * scale))))
        self.image = image

    def rect_for(self, corner: int) -> pygame.Rect:
        w, h = self.size
        name = CORNERS[corner]
        rect = self.image.get_rect()
        y = h - h // 20 if name.startswith("bottom") else h // 20
        if name.endswith("right"):
            rect.midright = (w - w // 40, y)
        else:
            rect.midleft = (w // 40, y)
        return rect

    def current_corner(self, now: float) -> int:
        return int(max(0.0, now - self.started) // CORNER_SECONDS) % len(CORNERS)

    def update(self, surface: pygame.Surface, now: float, cleared: bool) -> list[pygame.Rect]:
        """Draw when the corner changes or the board was cleared. Returns changed rects."""
        corner = self.current_corner(now)
        if corner == self.corner and not cleared:
            return []
        rects = []
        if self.corner is not None and corner != self.corner:
            old = self.rect_for(self.corner)
            surface.fill(BLACK, old)
            rects.append(old)
        new = self.rect_for(corner)
        surface.blit(self.image, new)
        rects.append(new)
        self.corner = corner
        return rects
