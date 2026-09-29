"""The dim "update available" line the screensaver shows on the primary monitor. It sits in
the margin the maze never uses (while it shows, a board fills at most
board.NOTICE_COVERAGE percent of each side; the Stage draws it only beside such a maze or
on black) and moves to the next corner every few minutes so it cannot burn in."""
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
        self.area: Optional[Rect] = None  # the area last drawn in
        self._scaled: dict[int, pygame.Surface] = {}
        font = pygame.font.SysFont(FONT_NAME, max(12, min(w, h) // 54))
        self.image = font.render(message, True, COLOR)

    def _image(self, width: int) -> pygame.Surface:
        """The message, shrunk to 90% of `width` when it is wider (cached per width)."""
        limit = width * 9 // 10
        image = self._scaled.get(limit)
        if image is None:
            image = self.image
            if image.get_width() > limit:
                scale = limit / image.get_width()
                image = pygame.transform.smoothscale(
                    image, (limit, max(1, round(image.get_height() * scale))))
            self._scaled[limit] = image
        return image

    def rect_for(self, corner: int, area: Optional[Rect] = None) -> pygame.Rect:
        ax, ay = (0, 0) if area is None else (area.x, area.y)
        w, h = self.size if area is None else (area.w, area.h)
        name = CORNERS[corner]
        rect = self._image(w).get_rect()
        y = ay + (h - h // 20 if name.startswith("bottom") else h // 20)
        if name.endswith("right"):
            rect.midright = (ax + w - w // 40, y)
        else:
            rect.midleft = (ax + w // 40, y)
        return rect

    def current_corner(self, now: float) -> int:
        return int(max(0.0, now - self.started) // CORNER_SECONDS) % len(CORNERS)

    def update(self, surface: pygame.Surface, now: float, cleared: bool,
               area: Optional[Rect] = None) -> list[pygame.Rect]:
        """Draw when the corner or the area changes, or the board was cleared. `area` is the
        board's part of the monitor while What's new shows beside it. Returns changed rects."""
        corner = self.current_corner(now)
        if corner == self.corner and area == self.area and not cleared:
            return []
        rects = []
        if self.corner is not None and (corner != self.corner or area != self.area):
            old = self.rect_for(self.corner, self.area)
            surface.fill(BLACK, old)
            rects.append(old)
        new = self.rect_for(corner, area)
        surface.blit(self._image(area.w if area is not None else self.size[0]), new)
        rects.append(new)
        self.corner, self.area = corner, area
        return rects
