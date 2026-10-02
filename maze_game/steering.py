"""Choosers: what decides where the dot goes each time it reaches a cell center."""
from __future__ import annotations

import math
from typing import Iterable, Iterator, Optional

from maze_saver.maze import Cell, Grid, direction, step

from .assist import dead_end_within

_UNREAD = object()  # PathSteer has not drawn its next cell yet


class KeyboardSteer:
    """Keyboard steering.

    The Steering setting picks one of three modes. Hold to move (follow bends and run
    straight off): the most recently pressed held direction steers; the dot stops
    where that way is closed. Bend assist (follow bends on): held keys keep the dot
    moving along its heading and through corridor bends; only a fresh press (the
    request) turns it into a side passage; forks pause for `pause` seconds so the player can react, then carry
    straight on if a key is still held. Branches that visibly dead-end within the
    look-ahead distance are not counted as choices.

    Run straight (follow bends off, run_straight on): one press is enough. The dot runs
    straight on with no key held and stops at the first bend, wall or junction, and at
    the start and finish. A press while it runs turns it at the first cell where that
    way is open; at a stop where it is not open, the press is dropped.
    """

    def __init__(self):
        self.held: list[int] = []
        self.request: Optional[int] = None
        self.now = 0.0
        self._pause_cell: Optional[Cell] = None
        self._pause_until = 0.0
        self._stopped = False
        self._last_cell: Optional[Cell] = None
        self._coasting = False  # Run straight: a press set the dot running

    def press(self, d: int) -> None:
        if d in self.held:
            self.held.remove(d)
        self.held.append(d)
        self.request = d
        self._coasting = True

    def release(self, d: int) -> None:
        if d in self.held:
            self.held.remove(d)

    def clear(self) -> None:
        self.held.clear()
        self.request = None
        self._pause_cell = None
        self._stopped = False
        self._last_cell = None
        self._coasting = False

    def reset_round(self) -> None:
        """A new round, or a replay of one, is starting. Any turn request buffered
        from before this point is stale (it belongs to the round that just ended, or
        to a growth phase the player could not see through) and must not fire on the
        first frame of play. The pause, stopped and last-cell tracking are stale for
        the same reason. Held keys are left alone, matching forget_position()."""
        self.request = None
        self.forget_position()

    def forget_position(self) -> None:
        """Mouse or dash steering just moved the dot on its own. Any pause, stop or
        last-cell tracking left over from keyboard steering is stale and must not
        linger when the keyboard chooser is next consulted, even if the dot ends up
        back at the same cell it left. A Run straight run ends here too, so the dot
        is not run on when they let go of it. Held keys are left alone."""
        self._pause_cell = None
        self._stopped = False
        self._last_cell = None
        self._coasting = False

    def tick(self, dt: float) -> None:
        self.now += dt

    @property
    def wanted(self) -> Optional[int]:
        return self.held[-1] if self.held else None

    def choose(self, grid: Grid, cell: Cell, came_from: Optional[Cell], follow_bends: bool,
               stops: Iterable[Cell], end: Cell, lookahead: int,
               pause: float, run_straight: bool = False) -> Optional[Cell]:
        if not follow_bends and run_straight:
            return self._straight(grid, cell, came_from, stops)
        # Any other steering: a press made under it must not start a run later, should
        # the setting change to Run straight while the dot sits mid-corridor.
        self._coasting = False
        if not follow_bends:
            d = self.wanted
            if d is not None and grid.open_dirs(cell) & d:
                return step(cell, d)
            return None
        # The pause and the stopped state are only meaningful across repeated idle
        # frames at the same cell. The game calls this chooser every idle frame at
        # the dot's current cell, including right after mouse or dash steering lets
        # go of it; if that cell differs from the one we were last consulted about,
        # any pause or stop left over from before is stale and must not linger.
        if self._last_cell != cell:
            self._pause_cell = None
            self._stopped = False
        self._last_cell = cell
        result = self._guided(grid, cell, came_from, stops, end, lookahead, pause)
        if result is not None:
            self._stopped = False
        return result

    def _straight(self, grid: Grid, cell: Cell, came_from: Optional[Cell],
                  stops: Iterable[Cell]) -> Optional[Cell]:
        """Run straight: on to the first bend, wall or junction. Junctions are counted
        from every opening except the way it came, without look-ahead, so a short dead
        end ahead does not hide a live branch."""
        if not self._coasting:
            return None
        r = self.request
        if r is not None and grid.open_dirs(cell) & r:
            self.request = None
            return step(cell, r)
        if (came_from is None or cell in stops
                or not grid.open_dirs(cell) & direction(came_from, cell)
                or len([n for n in grid.open_neighbors(cell) if n != came_from]) >= 2):
            self.request = None
            self._coasting = False
            return None
        return step(cell, direction(came_from, cell))

    def _guided(self, grid: Grid, cell: Cell, came_from: Optional[Cell], stops: Iterable[Cell],
                end: Cell, lookahead: int, pause: float) -> Optional[Cell]:
        r = self.request
        if r is not None:
            if grid.open_dirs(cell) & r:
                self.request = None
                self._pause_cell = None
                return step(cell, r)
            if self._stopped:
                # The dot is standing still: an unusable press does nothing rather
                # than launching it along its old, stale heading.
                self.request = None
                return None
        if came_from is None or cell in stops:
            self.request = None
            self._stopped = True
            return None
        heading = direction(came_from, cell)
        raw = [n for n in grid.open_neighbors(cell) if n != came_from]
        pruned = [n for n in raw if not dead_end_within(grid, cell, n, end, lookahead)]
        # Pruning only classifies forks (so an obvious dead end is not a real choice);
        # it must never remove the only way forward and stall a plain corridor.
        exits = pruned or raw
        if not exits:
            self.request = None
            self._stopped = True
            return None
        if len(exits) == 1:
            if self._stopped:
                # Merely still being held is not enough once genuinely stopped;
                # only a fresh, usable press (handled above) moves it again.
                self.request = None
                return None
            if not self.held:
                self.request = None
                self._stopped = True
                return None
            nxt = exits[0]
            if direction(cell, nxt) != heading:
                self.request = None
            return nxt
        if pause > 0:
            if self._pause_cell != cell:
                self._pause_cell = cell
                self._pause_until = self.now + pause
                return None
            if self.now < self._pause_until:
                return None
        self.request = None
        if self._stopped:
            return None
        ahead = step(cell, heading)
        if self.held and ahead in exits:
            self._pause_cell = None
            return ahead
        self._stopped = True
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
    """Follows a sequence of cells (a dash, the benchmark's perfect run, or screensaver
    mode's solve). Cells are drawn from it only as needed, at most one ahead of the
    dot, so a generator is not run up front."""

    def __init__(self, cells: Iterable[Cell]):
        self._cells: Iterator[Cell] = iter(cells)
        self._next: object = _UNREAD

    def _peek(self) -> Optional[Cell]:
        if self._next is _UNREAD:
            self._next = next(self._cells, None)
        return self._next  # type: ignore[return-value]

    @property
    def done(self) -> bool:
        return self._peek() is None

    def choose(self, cell: Cell, came_from: Optional[Cell] = None) -> Optional[Cell]:
        nxt = self._peek()
        if nxt is None:
            return None
        if abs(nxt[0] - cell[0]) + abs(nxt[1] - cell[1]) != 1:
            self._cells = iter(())
            self._next = None
            return None
        self._next = _UNREAD
        return nxt


class AutoSteer:
    """Drives the dot along the shortest route from wherever it is to the end."""

    def __init__(self, toward_end: dict, end: Cell):
        self.toward_end = toward_end
        self.end = end
        self.done = False

    def choose(self, cell: Cell, came_from: Optional[Cell] = None) -> Optional[Cell]:
        if self.done:
            return None
        if cell == self.end:
            self.done = True
            return None
        return self.toward_end.get(cell)
