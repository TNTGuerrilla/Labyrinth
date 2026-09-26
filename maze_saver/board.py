"""One monitor's maze: sizing, endpoint placement, and the phase state machine.

Pure logic with no pygame dependency. Board.update() reports which cells changed
so the renderer only redraws those.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .maze import Cell

FILL_NUM, FILL_DEN = 4, 5  # boards fill 80% of the monitor
MIN_CELL_PX = 4
MAX_STEPS_PER_FRAME = 500
MAX_ENDPOINT_TRIES = 1000


def fill(px: int) -> int:
    """80% of a pixel length, rounded down (integer math avoids float error)."""
    return px * FILL_NUM // FILL_DEN


@dataclass(frozen=True)
class Geometry:
    cols: int
    rows: int
    cell: int
    x: int  # board offset from the monitor's top-left
    y: int

    @property
    def width(self) -> int:
        return self.cols * self.cell

    @property
    def height(self) -> int:
        return self.rows * self.cell

    def cell_rect(self, c: Cell) -> tuple[int, int, int, int]:
        return (self.x + c[0] * self.cell, self.y + c[1] * self.cell, self.cell, self.cell)


def compute_geometry(width: int, height: int, min_cells: int, max_cells: int,
                     rng: random.Random) -> Geometry:
    """Square cells; short side fills 80%; long side random from square up to 80%."""
    short_fill = fill(min(width, height))
    long_fill = fill(max(width, height))
    n_short = rng.randint(min_cells, max_cells)
    n_short = max(2, min(n_short, short_fill // MIN_CELL_PX))
    cell = max(1, short_fill // n_short)
    n_long = rng.randint(n_short, max(n_short, long_fill // cell))
    if width >= height:
        cols, rows = n_long, n_short
    else:
        cols, rows = n_short, n_long
    return Geometry(cols, rows, cell, (width - cols * cell) // 2, (height - rows * cell) // 2)


def choose_endpoints(cols: int, rows: int, rng: random.Random) -> tuple[Cell, Cell]:
    """Two random cells at least half the board's span apart (Manhattan)."""
    need = (cols + rows) // 2
    for _ in range(MAX_ENDPOINT_TRIES):
        a = (rng.randrange(cols), rng.randrange(rows))
        b = (rng.randrange(cols), rng.randrange(rows))
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) >= need:
            return a, b
    return (0, 0), (cols - 1, rows - 1)


class StepAccumulator:
    """Turns a steps-per-second rate into whole steps per frame."""

    def __init__(self, rate: float):
        self.rate = rate
        self._acc = 0.0

    def take(self, dt: float) -> int:
        self._acc += dt * self.rate
        steps = int(self._acc)
        self._acc -= steps
        return min(steps, MAX_STEPS_PER_FRAME)
