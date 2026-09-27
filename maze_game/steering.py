"""Choosers: what decides where the dot goes each time it reaches a cell center."""
from __future__ import annotations

import math
import random
from collections import deque
from typing import Iterable, Iterator, Optional

from maze_saver.maze import Cell, Grid, direction, step
from maze_saver.solver import SolveEvent, Solved, solve

from .assist import dead_end_within


class KeyboardSteer:
    """Keyboard steering.

    Follow bends off: the most recently pressed held direction steers; the dot stops
    where that way is closed. Follow bends on: held keys keep the dot moving along its
    heading and through corridor bends; only a fresh press (the request) turns it into
    a side passage; forks pause for `pause` seconds so the player can react, then carry
    straight on if a key is still held. Branches that visibly dead-end within the
    look-ahead distance are not counted as choices.
    """

    def __init__(self):
        self.held: list[int] = []
        self.request: Optional[int] = None
        self.now = 0.0
        self._pause_cell: Optional[Cell] = None
        self._pause_until = 0.0
        self._resting = False

    def press(self, d: int) -> None:
        if d in self.held:
            self.held.remove(d)
        self.held.append(d)
        self.request = d

    def release(self, d: int) -> None:
        if d in self.held:
            self.held.remove(d)

    def clear(self) -> None:
        self.held.clear()
        self.request = None
        self._pause_cell = None

    def tick(self, dt: float) -> None:
        self.now += dt

    @property
    def wanted(self) -> Optional[int]:
        return self.held[-1] if self.held else None

    def choose(self, grid: Grid, cell: Cell, came_from: Optional[Cell], follow_bends: bool,
               stops: Iterable[Cell], end: Cell, lookahead: int,
               pause: float) -> Optional[Cell]:
        if not follow_bends:
            d = self.wanted
            if d is not None and grid.open_dirs(cell) & d:
                return step(cell, d)
            return None
        result = self._guided(grid, cell, came_from, stops, end, lookahead, pause)
        self._resting = result is None
        return result

    def _guided(self, grid: Grid, cell: Cell, came_from: Optional[Cell], stops: Iterable[Cell],
                end: Cell, lookahead: int, pause: float) -> Optional[Cell]:
        if self._pause_cell is not None and self._pause_cell != cell:
            self._pause_cell = None
        r = self.request
        if r is not None:
            if grid.open_dirs(cell) & r:
                self.request = None
                self._pause_cell = None
                return step(cell, r)
            if self._resting:
                # The dot is standing still: an unusable press does nothing rather
                # than launching it along its old, stale heading.
                self.request = None
                return None
        if came_from is None or cell in stops:
            self.request = None
            return None
        heading = direction(came_from, cell)
        raw = [n for n in grid.open_neighbors(cell) if n != came_from]
        pruned = [n for n in raw if not dead_end_within(grid, cell, n, end, lookahead)]
        # Pruning only classifies forks (so an obvious dead end is not a real choice);
        # it must never remove the only way forward and stall a plain corridor.
        exits = pruned or raw
        if not exits:
            self.request = None
            return None
        if len(exits) == 1:
            if not self.held:
                self.request = None
                return None
            nxt = exits[0]
            if direction(cell, nxt) != heading:
                self.request = None
            return nxt
        if self._pause_cell != cell:
            self._pause_cell = cell
            self._pause_until = self.now + pause
        if self.now < self._pause_until:
            return None
        self.request = None
        if self.held and grid.open_dirs(cell) & heading:
            self._pause_cell = None
            return step(cell, heading)
        return None


def is_reverse(frm: Cell, to: Optional[Cell], d: int) -> bool:
    """True if pressing direction d means turning around on the segment frm -> to."""
    return to is not None and direction(to, frm) == d


def steer_toward(grid: Grid, cell: Cell, target: tuple[float, float]) -> Optional[Cell]:
    """Open neighbor whose center is closest to `target` (cell units), if it is closer
    than `cell`'s own center. Distance strictly shrinks, so this never oscillates."""
    def dist(c: Cell) -> float:
        return math.hypot(c[0] + 0.5 - target[0], c[1] + 0.5 - target[1])

    best, best_dist = None, dist(cell)
    for n in grid.open_neighbors(cell):
        d = dist(n)
        if d < best_dist - 1e-9:
            best, best_dist = n, d
    return best


def dash_path(grid: Grid, frm: Cell, target: Cell) -> Optional[list[Cell]]:
    """Cells after `frm` up to `target` along one straight run of open passages."""
    if frm == target or not grid.in_bounds(target):
        return None
    if frm[0] != target[0] and frm[1] != target[1]:
        return None
    dx = (target[0] > frm[0]) - (target[0] < frm[0])
    dy = (target[1] > frm[1]) - (target[1] < frm[1])
    d = direction(frm, (frm[0] + dx, frm[1] + dy))
    path = []
    cur = frm
    while cur != target:
        if not grid.open_dirs(cur) & d:
            return None
        cur = step(cur, d)
        path.append(cur)
    return path


class PathSteer:
    """Follows a fixed list of cells (a dash, or the benchmark's perfect run)."""

    def __init__(self, cells: Iterable[Cell]):
        self._cells = deque(cells)

    @property
    def done(self) -> bool:
        return not self._cells

    def choose(self, cell: Cell, came_from: Optional[Cell] = None) -> Optional[Cell]:
        if not self._cells:
            return None
        nxt = self._cells[0]
        if abs(nxt[0] - cell[0]) + abs(nxt[1] - cell[1]) != 1:
            self._cells.clear()
            return None
        self._cells.popleft()
        return nxt


class AutoSteer:
    """Drives the screensaver's human-like solver from wherever the dot is."""

    def __init__(self, grid: Grid, end: Cell, rng: random.Random, lookahead: int):
        self.grid = grid
        self.end = end
        self.rng = rng
        self.lookahead = lookahead
        self.done = False
        self._events: Optional[Iterator[SolveEvent]] = None

    def choose(self, cell: Cell, came_from: Optional[Cell] = None) -> Optional[Cell]:
        if self.done:
            return None
        if self._events is None:
            self._events = solve(self.grid, cell, self.end, self.rng, lookahead=self.lookahead)
        event = next(self._events, None)
        if event is None or isinstance(event, Solved):
            self.done = True
            return None
        return event.b
