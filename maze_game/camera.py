"""Zoom and scroll for the play area.

Positions are in cell units: cell (x, y) spans x..x+1 and y..y+1, so its center is
(x + 0.5, y + 0.5). Pixels are relative to the play area's top-left corner. Cell size
is a whole number of pixels, so cells tile without gaps.
"""
from __future__ import annotations

from typing import Iterator

from maze_saver.maze import Cell

FILL = 0.8  # 100% zoom fits the maze into 80% of the play area
MAX_CELL_PX = 48
ZOOM_STEP = 1.25
FOLLOW_ZONE = 0.4  # the dot stays inside the central 40% of the view
FOLLOW_RATE = 8.0  # how quickly the camera catches up, per second


class Camera:
    def __init__(self, cols: int, rows: int, view_w: int, view_h: int):
        self.cols, self.rows = cols, rows
        self.fit_px = self.cell_px = 1
        self.cx, self.cy = cols / 2, rows / 2
        self.resize(view_w, view_h)

    def resize(self, view_w: int, view_h: int) -> None:
        """New play-area size; keeps the zoom ratio."""
        ratio = self.cell_px / self.fit_px
        self.view_w, self.view_h = max(1, view_w), max(1, view_h)
        self.fit_px = max(1, int(min(self.view_w * FILL / self.cols,
                                     self.view_h * FILL / self.rows)))
        self.cell_px = self._clamp_px(round(self.fit_px * ratio))
        self._clamp_center()

    @property
    def max_px(self) -> int:
        return max(self.fit_px, MAX_CELL_PX)

    @property
    def zoom(self) -> float:
        return self.cell_px / self.fit_px

    @property
    def zoomed(self) -> bool:
        return self.cell_px > self.fit_px

    def _clamp_px(self, px: int) -> int:
        return max(self.fit_px, min(self.max_px, px))

    def origin(self) -> tuple[int, int]:
        """Pixel position of cell-space (0, 0)."""
        return (round(self.view_w / 2 - self.cx * self.cell_px),
                round(self.view_h / 2 - self.cy * self.cell_px))

    def to_screen(self, x: float, y: float) -> tuple[float, float]:
        ox, oy = self.origin()
        return (ox + x * self.cell_px, oy + y * self.cell_px)

    def to_cells(self, px: float, py: float) -> tuple[float, float]:
        ox, oy = self.origin()
        return ((px - ox) / self.cell_px, (py - oy) / self.cell_px)

    def cell_rect(self, c: Cell) -> tuple[int, int, int, int]:
        ox, oy = self.origin()
        p = self.cell_px
        return (ox + c[0] * p, oy + c[1] * p, p, p)

    def cells_in_rect(self, x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        """Half-open cell ranges (x0, y0, x1, y1) touching a pixel rectangle."""
        ox, oy = self.origin()
        p = self.cell_px
        return (max(0, (x - ox) // p), max(0, (y - oy) // p),
                min(self.cols, (x + w - 1 - ox) // p + 1),
                min(self.rows, (y + h - 1 - oy) // p + 1))

    def visible_cells(self) -> Iterator[Cell]:
        x0, y0, x1, y1 = self.cells_in_rect(0, 0, self.view_w, self.view_h)
        for y in range(y0, y1):
            for x in range(x0, x1):
                yield (x, y)

    def zoom_by(self, steps: int, anchor: tuple[float, float]) -> None:
        """Zoom in (steps > 0) or out, keeping `anchor` at the same pixel position."""
        new = self.cell_px
        for _ in range(abs(steps)):
            nxt = round(new * ZOOM_STEP) if steps > 0 else round(new / ZOOM_STEP)
            if nxt == new:
                nxt += 1 if steps > 0 else -1
            new = self._clamp_px(nxt)
        if new == self.cell_px:
            return
        sx, sy = self.to_screen(*anchor)
        self.cell_px = new
        self.cx = anchor[0] - (sx - self.view_w / 2) / new
        self.cy = anchor[1] - (sy - self.view_h / 2) / new
        self._clamp_center()

    def reset_zoom(self) -> None:
        self.cell_px = self.fit_px
        self._clamp_center()

    def follow(self, pos: tuple[float, float], dt: float) -> None:
        """Ease the view so `pos` stays inside the central zone. Fixed at 100% zoom."""
        if not self.zoomed:
            return
        hw = self.view_w * FOLLOW_ZONE / 2 / self.cell_px
        hh = self.view_h * FOLLOW_ZONE / 2 / self.cell_px
        tx = min(max(self.cx, pos[0] - hw), pos[0] + hw)
        ty = min(max(self.cy, pos[1] - hh), pos[1] + hh)
        k = min(1.0, dt * FOLLOW_RATE)
        self.cx += (tx - self.cx) * k
        self.cy += (ty - self.cy) * k
        self._clamp_center()

    def _clamp_center(self) -> None:
        if not self.zoomed:
            self.cx, self.cy = self.cols / 2, self.rows / 2
            return
        hw = self.view_w / 2 / self.cell_px
        hh = self.view_h / 2 / self.cell_px
        self.cx = min(max(self.cx, min(hw, self.cols / 2)), max(self.cols - hw, self.cols / 2))
        self.cy = min(max(self.cy, min(hh, self.rows / 2)), max(self.rows - hh, self.rows / 2))
