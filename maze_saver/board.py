"""One monitor's maze: sizing, endpoint placement, and the phase state machine.

Pure logic with no pygame dependency. Board.update() reports which cells changed
so the renderer only redraws those.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Iterator, Optional

from .config import Settings
from .maze import (Carve, Cell, Finish, GenEvent, Grid, Retreat, Start, Weld, choose_generator,
                   edge_key)
from .solver import Advance, Solved, SolveEvent, solve

FILL_NUM, FILL_DEN = 4, 5  # boards fill 80% of the monitor
MIN_CELL_PX = 4
MAX_STEPS_PER_FRAME = 500
MAX_ENDPOINT_TRIES = 1000

BLACK_SECONDS = 1.0
FIRST_DELAY_MAX = 2.0
DOTS_SECONDS = 0.8
WELD_FLASH_SECONDS = 0.3

Edge = tuple[Cell, Cell]


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


class Phase(Enum):
    BLACK = auto()
    DOTS = auto()
    GENERATE = auto()
    SOLVE = auto()
    HOLD = auto()


@dataclass
class Changes:
    """What to redraw this frame: the whole board area and/or specific cells."""
    clear: bool = False
    cells: set = field(default_factory=set)


class Board:
    """One monitor's maze cycle: black, dots, generate, solve, hold, repeat."""

    def __init__(self, width: int, height: int, settings: Settings, rng: random.Random,
                 initial_delay: float = 0.0, forced_leads: Optional[int] = None):
        self.width = width
        self.height = height
        self.settings = settings
        self.rng = rng
        self.forced_leads = forced_leads
        self.time = 0.0
        self._reset()
        self._enter_black(initial_delay)

    def _reset(self) -> None:
        self.geometry: Optional[Geometry] = None
        self.grid: Optional[Grid] = None
        self.start: Optional[Cell] = None
        self.end: Optional[Cell] = None
        self.region_of: dict[Cell, int] = {}
        self.hues: list[float] = []
        self.heads: dict[int, Cell] = {}
        self.welds: dict[Edge, float] = {}
        self.trail: dict[Edge, bool] = {}
        self.dot: Optional[Cell] = None
        self.solved = False
        self._gen_events: Optional[Iterator[GenEvent]] = None
        self._solve_events: Optional[Iterator[SolveEvent]] = None
        self._steps: Optional[StepAccumulator] = None

    @property
    def head_cells(self) -> set:
        return set(self.heads.values())

    def update(self, dt: float) -> Changes:
        self.time += dt
        changes = Changes()
        self._expire_welds(changes)
        if self.phase is Phase.GENERATE:
            self._run_generator(dt, changes)
        elif self.phase is Phase.SOLVE:
            self._run_solver(dt, changes)
        else:
            self._timer -= dt
            if self._timer <= 0:
                if self.phase is Phase.BLACK:
                    self._enter_dots(changes)
                elif self.phase is Phase.DOTS:
                    self._enter_generate()
                else:
                    self._reset()
                    self._enter_black(0.0)
        if self._pending_clear:
            self._pending_clear = False
            changes.clear = True
            changes.cells.clear()
        return changes

    def _enter_black(self, extra_delay: float) -> None:
        self.phase = Phase.BLACK
        self._timer = BLACK_SECONDS + extra_delay
        self._pending_clear = True

    def _enter_dots(self, changes: Changes) -> None:
        s = self.settings
        self.geometry = compute_geometry(self.width, self.height, s.min_cells, s.max_cells, self.rng)
        self.grid = Grid(self.geometry.cols, self.geometry.rows)
        self.start, self.end = choose_endpoints(self.geometry.cols, self.geometry.rows, self.rng)
        count, self._gen_events = choose_generator(self.grid, self.rng, self.settings.max_leads,
                                                    self.forced_leads)
        base = self.rng.random()
        self.hues = [(base + i / count) % 1.0 for i in range(count)]
        self.phase = Phase.DOTS
        self._timer = DOTS_SECONDS
        changes.cells.update((self.start, self.end))

    def _enter_generate(self) -> None:
        self.phase = Phase.GENERATE
        self._steps = StepAccumulator(self.settings.gen_speed)

    def _run_generator(self, dt: float, changes: Changes) -> None:
        for _ in range(self._steps.take(dt)):
            event = next(self._gen_events, None)
            if event is None:
                self._enter_solve(changes)
                return
            self._apply_generation(event, changes)

    def _apply_generation(self, event: GenEvent, changes: Changes) -> None:
        if isinstance(event, Start):
            self.region_of[event.cell] = event.region
            self.heads[event.region] = event.cell
            changes.cells.add(event.cell)
        elif isinstance(event, Carve):
            self.region_of[event.b] = event.region
            self.heads[event.region] = event.b
            changes.cells.update((event.a, event.b))
        elif isinstance(event, Retreat):
            self.heads[event.region] = event.to
            changes.cells.update((event.frm, event.to))
        elif isinstance(event, Finish):
            self.heads.pop(event.region, None)
            changes.cells.add(event.cell)
        elif isinstance(event, Weld):
            self.welds[edge_key(event.a, event.b)] = self.time + WELD_FLASH_SECONDS
            changes.cells.update((event.a, event.b))

    def _expire_welds(self, changes: Changes) -> None:
        for edge, until in list(self.welds.items()):
            if until <= self.time:
                del self.welds[edge]
                changes.cells.update(edge)

    def _enter_solve(self, changes: Changes) -> None:
        self.phase = Phase.SOLVE
        self.heads.clear()
        self.dot = self.start
        self._solve_events = solve(self.grid, self.start, self.end, self.rng)
        self._steps = StepAccumulator(self.settings.solve_speed)
        changes.cells.add(self.start)

    def _run_solver(self, dt: float, changes: Changes) -> None:
        for _ in range(self._steps.take(dt)):
            event = next(self._solve_events, None)
            if event is None or isinstance(event, Solved):
                self.solved = True
                self.phase = Phase.HOLD
                self._timer = self.settings.hold_seconds
                return
            self.trail[edge_key(event.a, event.b)] = isinstance(event, Advance)
            self.dot = event.b
            changes.cells.update((event.a, event.b))
