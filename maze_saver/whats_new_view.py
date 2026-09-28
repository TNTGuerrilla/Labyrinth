"""Draws the What's new section beside the primary maze (the rules are in whats_new). The
whole section is drawn once into its own surface; later frames copy only what changed: the
footer once a second, everything after the board clears the screen, and every frame of the
1.5 second fade."""
from __future__ import annotations

from typing import Sequence

import pygame

from labyrinth_update.notes import (BLANK, BULLET, HEADING, ITEM, MORE_TEXT, TEXT, NoteLine,
                                    fit_lines, wrap_notes)

from .watermark import BLACK, COLOR, FONT_NAME
from .whats_new import SectionClock, footer_layout, split_monitor

_UNSET = object()


class WhatsNewSection:
    def __init__(self, title: str, lines: Sequence[NoteLine], clock: SectionClock,
                 size: tuple[int, int]):
        if not pygame.font.get_init():
            pygame.font.init()
        self.split = split_monitor(*size)
        self.clock = clock
        box = self.split.section
        self.rect = pygame.Rect(box.x, box.y, box.w, box.h)
        base = min(size)
        body_size = max(12, base // 54)  # the watermark's size
        self._body = pygame.font.SysFont(FONT_NAME, body_size)
        heading = pygame.font.SysFont(FONT_NAME, body_size, bold=True)
        title_font = pygame.font.SysFont(FONT_NAME, max(14, base // 40))
        pad = max(8, base // 60)
        inner_w = self.rect.w - 2 * pad
        line_h = self._body.get_linesize()
        self.image = pygame.Surface(self.rect.size)
        self.image.fill(BLACK)
        pygame.draw.rect(self.image, COLOR, self.image.get_rect(), 1)
        y = pad
        for row in wrap_notes([NoteLine(TEXT, title)], inner_w,
                              lambda s: title_font.size(s)[0]):
            self.image.blit(title_font.render(row.text, True, COLOR), (pad, y))
            y += title_font.get_linesize()
        y += line_h // 2
        self._footer = pygame.Rect(pad, self.rect.h - pad - line_h, inner_w, line_h)
        room = max(0, (self._footer.y - line_h // 2 - y) // line_h)
        measure = lambda s: heading.size(s)[0]  # noqa: E731  the wider font, so all fit
        more = wrap_notes([NoteLine(TEXT, MORE_TEXT)], inner_w, measure)
        self.shown_lines = fit_lines(wrap_notes(lines, inner_w, measure), room, more)
        indent = self._body.size(BULLET)[0]
        for row in self.shown_lines:
            if row.kind == HEADING:
                self.image.blit(heading.render(row.text, True, COLOR), (pad, y))
            elif row.kind == ITEM:
                if not row.cont:
                    self.image.blit(self._body.render(BULLET, True, COLOR), (pad, y))
                self.image.blit(self._body.render(row.text, True, COLOR), (pad + indent, y))
            elif row.kind != BLANK:
                self.image.blit(self._body.render(row.text, True, COLOR), (pad, y))
            y += line_h
        self._seconds = _UNSET
        self._alpha = 255
        self._drawn = False

    def _draw_footer(self, seconds) -> None:
        f = footer_layout(seconds, lambda s: self._body.size(s)[0])
        r = self._footer
        self.image.fill(BLACK, r)
        self.image.blit(self._body.render(f.words, True, COLOR), r.topleft)
        if f.number:
            number = self._body.render(f.number, True, COLOR)
            # Right-aligned in a slot as wide as "99", so the words never move.
            self.image.blit(number, (r.x + f.number_right - number.get_width(), r.y))

    def update(self, surface: pygame.Surface, now: float, cleared: bool) -> list[pygame.Rect]:
        """Draw what changed on the primary board's surface. Returns changed rects."""
        seconds = self.clock.seconds_left(now)
        alpha = self.clock.alpha(now)
        footer_changed = seconds != self._seconds
        if footer_changed:
            self._seconds = seconds
            self._draw_footer(seconds)
        if cleared or not self._drawn or alpha != self._alpha:
            self._drawn, self._alpha = True, alpha
            surface.fill(BLACK, self.rect)
            self.image.set_alpha(alpha)
            surface.blit(self.image, self.rect)
            return [self.rect.copy()]
        if footer_changed:
            dest = self._footer.move(self.rect.topleft)
            surface.blit(self.image, dest, self._footer)
            return [dest]
        return []
