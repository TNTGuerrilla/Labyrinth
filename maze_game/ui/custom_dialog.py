"""The Custom size dialog (key 5): Min and Max short-side cells, benchmark advice."""
from __future__ import annotations

from typing import Optional

import pygame

from ..benchmark import build_seconds, build_text
from ..difficulty import MIN_CUSTOM, grid_size
from .widgets import (HILITE, MUTED, WARN, Hits, button_rect, dim, draw_button, draw_panel,
                      text)

REPEAT_WINDOW = 0.15  # presses closer together than this count as holding the key
MAX_TYPED = 99999


class CustomDialog:
    def __init__(self, cmin: int, cmax: int, ceiling: int, bench_size: Optional[int],
                 bench_rate: Optional[float], view: tuple[int, int]):
        self.ceiling = ceiling
        self.values = [self._clamp(cmin), self._clamp(cmax)]
        self.field = 0
        self.bench_size = bench_size
        self.bench_rate = bench_rate
        self.view = view
        self.hits = Hits()
        self._typing = False
        self._streak = 0
        self._last: tuple[Optional[int], float] = (None, -1.0)

    def _clamp(self, value: int) -> int:
        return max(MIN_CUSTOM, min(self.ceiling, int(value)))

    def _commit(self) -> None:
        self.values[self.field] = self._clamp(self.values[self.field])
        self._typing = False

    def _step(self, sign: int, now: float) -> int:
        last_sign, last_time = self._last
        held = last_sign == sign and now - last_time < REPEAT_WINDOW
        self._streak = self._streak + 1 if held else 0
        self._last = (sign, now)
        if self._streak < 10:
            return 1
        return 10 if self._streak < 30 else 50

    def handle(self, nav: str, now: float = 0.0) -> Optional[str]:
        if nav in ("up", "down"):
            self._commit()
            self.field = 1 - self.field
        elif nav in ("left", "right"):
            self._commit()
            sign = 1 if nav == "right" else -1
            self.values[self.field] = self._clamp(self.values[self.field]
                                                  + sign * self._step(sign, now))
        elif nav.startswith("digit:"):
            digit = int(nav[6:])
            current = self.values[self.field] if self._typing else 0
            self.values[self.field] = min(MAX_TYPED, current * 10 + digit)
            self._typing = True
        elif nav == "backspace":
            self.values[self.field] //= 10
            self._typing = True
        elif nav == "confirm":
            self._commit()
            self.values = sorted(self._clamp(v) for v in self.values)
            return "start"
        elif nav == "cancel":
            return "close"
        return None

    def result(self) -> tuple[int, int]:
        return self.values[0], self.values[1]

    def notes(self) -> list[tuple[str, tuple]]:
        if self.bench_size is None or self.bench_rate is None:
            return [("Performance at large sizes can't be predicted on this PC", MUTED),
                    ("until the benchmark is run.", MUTED)]
        lines = [(f"Recommended max: {self.bench_size}", MUTED)]
        if max(self.values) > self.bench_size:
            lines.append(("Above the recommended size. May run below 60 fps.", WARN))
        cols, rows = grid_size(max(self.values), *self.view)
        lines.append((build_text(build_seconds(cols * rows, self.bench_rate)), MUTED))
        return lines

    def draw(self, surface: pygame.Surface) -> None:
        dim(surface)
        box = pygame.Rect(0, 0, 500, 330)
        box.center = surface.get_rect().center
        draw_panel(surface, box)
        self.hits.clear()
        text(surface, "Custom size", (box.x + 24, box.y + 18), 22)
        text(surface, f"Short-side cells, {MIN_CUSTOM} to {self.ceiling}",
             (box.x + 24, box.y + 50), 14, MUTED)
        for i, name in enumerate(("Min", "Max")):
            row = pygame.Rect(box.x + 16, box.y + 84 + i * 44, box.w - 32, 36)
            if i == self.field:
                pygame.draw.rect(surface, HILITE, row, border_radius=5)
            text(surface, name, (row.x + 12, row.centery), 17, anchor="midleft")
            dec = pygame.Rect(row.right - 160, row.y + 4, 28, 28)
            inc = pygame.Rect(row.right - 40, row.y + 4, 28, 28)
            draw_button(surface, dec, "-")
            draw_button(surface, inc, "+")
            text(surface, str(self.values[i]), ((dec.right + inc.left) // 2, row.centery), 17,
                 anchor="center")
            self.hits.add(dec, ("dec", i))
            self.hits.add(inc, ("inc", i))
            self.hits.add(row, ("field", i))
        y = box.y + 178
        for line, color in self.notes():
            text(surface, line, (box.x + 24, y), 14, color)
            y += 20
        bench = button_rect("Run benchmark", (box.x + 24, box.bottom - 18), anchor="bottomleft")
        close = button_rect("Close", (box.right - 24, box.bottom - 18), anchor="bottomright")
        start = button_rect("Start", (close.x - 8, box.bottom - 18), anchor="bottomright")
        for rect, label, value in ((bench, "Run benchmark", "benchmark"),
                                   (start, "Start", "start"), (close, "Close", "close")):
            draw_button(surface, rect, label)
            self.hits.add(rect, value)

    def click(self, pos: tuple[int, int]) -> Optional[str]:
        hit = self.hits.at(pos)
        if hit is None:
            return None
        if hit == "benchmark":
            return "benchmark"
        if hit == "start":
            return self.handle("confirm")
        if hit == "close":
            return "close"
        kind, i = hit
        self._commit()
        self.field = i
        if kind == "dec":
            self.values[i] = self._clamp(self.values[i] - 1)
        elif kind == "inc":
            self.values[i] = self._clamp(self.values[i] + 1)
        return None
