"""The panel the game shows after an update, and again from Settings, Info, What's new."""
from __future__ import annotations

from typing import Optional, Sequence

import pygame

from labyrinth_update.notes import BLANK, BULLET, HEADING, ITEM, NoteLine, wrap_notes

from .widgets import (BORDER, MUTED, Hits, button_rect, dim, draw_button, draw_panel, font,
                      text)

BODY_SIZE = 15
HEADING_SIZE = 17
LINE_H = 22
WHEEL_LINES = 3


class WhatsNewDialog:
    def __init__(self, title: str, lines: Sequence[NoteLine], first_run: bool = False):
        self.title = title
        self.lines = list(lines)
        self.first_run = first_run  # closing it marks the update as seen
        self.scroll = 0  # index of the first wrapped row shown
        self.hits = Hits()
        self._max_scroll = 0
        self._wrapped: tuple[int, list[NoteLine]] = (-1, [])  # (width, rows) cache

    def handle(self, nav: str, now: float = 0.0) -> Optional[str]:
        if nav == "up":
            self.scroll = max(0, self.scroll - 1)
        elif nav == "down":
            self.scroll = min(self._max_scroll, self.scroll + 1)
        elif nav in ("confirm", "cancel"):
            return "close"
        return None

    def wheel(self, y: int) -> None:
        self.scroll = max(0, min(self._max_scroll, self.scroll - y * WHEEL_LINES))

    def click(self, pos: tuple[int, int]) -> Optional[str]:
        return "close" if self.hits.at(pos) == "ok" else None

    def _rows(self, width: int) -> list[NoteLine]:
        if self._wrapped[0] != width:
            # Wrapped with the heading font, the wider one, so a heading never overflows.
            measure = lambda s: font(HEADING_SIZE).size(s)[0]  # noqa: E731
            self._wrapped = (width, wrap_notes(self.lines, width, measure))
        return self._wrapped[1]

    def draw(self, surface: pygame.Surface) -> None:
        dim(surface)
        sw, sh = surface.get_size()
        box = pygame.Rect(0, 0, min(640, sw - 32), min(520, sh - 32))
        box.center = (sw // 2, sh // 2)
        draw_panel(surface, box)
        self.hits.clear()
        text(surface, self.title, (box.x + 24, box.y + 18), 22)
        body = pygame.Rect(box.x + 24, box.y + 60, box.w - 58, box.h - 60 - 64)
        rows = self._rows(body.w)
        visible = max(1, body.h // LINE_H)
        self._max_scroll = max(0, len(rows) - visible)
        self.scroll = min(self.scroll, self._max_scroll)
        indent = font(BODY_SIZE).size(BULLET)[0]
        for i, row in enumerate(rows[self.scroll:self.scroll + visible]):
            y = body.y + i * LINE_H
            if row.kind == HEADING:
                text(surface, row.text, (body.x, y), HEADING_SIZE)
            elif row.kind == ITEM:
                if not row.cont:
                    text(surface, BULLET, (body.x, y), BODY_SIZE, MUTED)
                text(surface, row.text, (body.x + indent, y), BODY_SIZE)
            elif row.kind != BLANK:
                text(surface, row.text, (body.x, y), BODY_SIZE)
        if self._max_scroll:
            track = pygame.Rect(body.right + 6, body.y, 4, visible * LINE_H)
            thumb_h = max(16, track.h * visible // len(rows))
            thumb_y = track.y + (track.h - thumb_h) * self.scroll // self._max_scroll
            pygame.draw.rect(surface, BORDER, track, border_radius=2)
            pygame.draw.rect(surface, MUTED, (track.x, thumb_y, track.w, thumb_h),
                             border_radius=2)
        ok = button_rect("OK", (box.right - 24, box.bottom - 18), anchor="bottomright")
        draw_button(surface, ok, "OK", active=True)
        self.hits.add(ok, "ok")
