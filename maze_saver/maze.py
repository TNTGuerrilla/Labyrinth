"""Maze grid and animated maze generators.

Generators carve into a Grid and yield one event per animation step. They have
no pygame dependency. Both styles produce a perfect maze (a spanning tree).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator, Union

Cell = tuple[int, int]

N, E, S, W = 1, 2, 4, 8
DELTAS: dict[int, tuple[int, int]] = {N: (0, -1), E: (1, 0), S: (0, 1), W: (-1, 0)}
OPPOSITE = {N: S, E: W, S: N, W: E}


def direction(a: Cell, b: Cell) -> int:
    delta = (b[0] - a[0], b[1] - a[1])
    for d, dd in DELTAS.items():
        if dd == delta:
            return d
    raise ValueError(f"cells {a} and {b} are not adjacent")


def step(c: Cell, d: int) -> Cell:
    dx, dy = DELTAS[d]
    return (c[0] + dx, c[1] + dy)


def edge_key(a: Cell, b: Cell) -> tuple[Cell, Cell]:
    return (a, b) if a <= b else (b, a)


class Grid:
    """cols x rows cells; each cell stores a bitmask of its open sides."""

    def __init__(self, cols: int, rows: int):
        if cols < 1 or rows < 1:
            raise ValueError(f"grid must be at least 1x1, got {cols}x{rows}")
        self.cols = cols
        self.rows = rows
        self._open = [[0] * cols for _ in range(rows)]

    def cells(self) -> Iterator[Cell]:
        for y in range(self.rows):
            for x in range(self.cols):
                yield (x, y)

    def in_bounds(self, c: Cell) -> bool:
        return 0 <= c[0] < self.cols and 0 <= c[1] < self.rows

    def neighbors(self, c: Cell) -> list[Cell]:
        return [n for n in (step(c, d) for d in DELTAS) if self.in_bounds(n)]

    def open_dirs(self, c: Cell) -> int:
        return self._open[c[1]][c[0]]

    def is_open(self, a: Cell, b: Cell) -> bool:
        return bool(self.open_dirs(a) & direction(a, b))

    def open_neighbors(self, c: Cell) -> list[Cell]:
        bits = self.open_dirs(c)
        return [step(c, d) for d in DELTAS if bits & d]

    def carve(self, a: Cell, b: Cell) -> None:
        d = direction(a, b)
        if not (self.in_bounds(a) and self.in_bounds(b)):
            raise ValueError(f"cannot carve outside the grid: {a} -> {b}")
        self._open[a[1]][a[0]] |= d
        self._open[b[1]][b[0]] |= OPPOSITE[d]

    def passage_count(self) -> int:
        return sum(bin(v).count("1") for row in self._open for v in row) // 2


@dataclass(frozen=True)
class Start:
    cell: Cell
    region: int


@dataclass(frozen=True)
class Carve:
    a: Cell
    b: Cell
    region: int


@dataclass(frozen=True)
class Retreat:
    frm: Cell
    to: Cell
    region: int


@dataclass(frozen=True)
class Finish:
    cell: Cell
    region: int


@dataclass(frozen=True)
class Weld:
    a: Cell
    b: Cell


GenEvent = Union[Start, Carve, Retreat, Finish, Weld]


class _Snake:
    """One recursive-backtracker head. step() performs one animation step."""

    def __init__(self, grid: Grid, start: Cell, region: int, visited: set, rng: random.Random):
        self.grid = grid
        self.region = region
        self.visited = visited
        self.rng = rng
        self.stack = [start]

    @property
    def done(self) -> bool:
        return not self.stack

    def step(self) -> GenEvent:
        cur = self.stack[-1]
        options = [n for n in self.grid.neighbors(cur) if n not in self.visited]
        if options:
            nxt = self.rng.choice(options)
            self.grid.carve(cur, nxt)
            self.visited.add(nxt)
            self.stack.append(nxt)
            return Carve(cur, nxt, self.region)
        self.stack.pop()
        if self.stack:
            return Retreat(cur, self.stack[-1], self.region)
        return Finish(cur, self.region)


def single_snake(grid: Grid, rng: random.Random) -> Iterator[GenEvent]:
    start = (rng.randrange(grid.cols), rng.randrange(grid.rows))
    snake = _Snake(grid, start, 0, {start}, rng)
    yield Start(start, 0)
    while not snake.done:
        yield snake.step()


def multi_snake(grid: Grid, rng: random.Random, heads: int) -> Iterator[GenEvent]:
    heads = max(1, min(heads, grid.cols * grid.rows))
    starts = rng.sample(list(grid.cells()), heads)
    visited = set(starts)
    region_of = {c: r for r, c in enumerate(starts)}
    snakes = [_Snake(grid, c, r, visited, rng) for r, c in enumerate(starts)]
    for r, c in enumerate(starts):
        yield Start(c, r)
    active = list(snakes)
    while active:
        for snake in list(active):
            event = snake.step()
            if isinstance(event, Carve):
                region_of[event.b] = event.region
            yield event
            if snake.done:
                active.remove(snake)
    yield from _weld_regions(grid, rng, region_of, heads)


def _weld_regions(grid: Grid, rng: random.Random, region_of: dict, count: int) -> Iterator[Weld]:
    """Open one wall per pair of regions needed to join them (Kruskal over regions)."""
    walls = []
    for c in grid.cells():
        for n in (step(c, E), step(c, S)):
            if grid.in_bounds(n) and region_of[c] != region_of[n]:
                walls.append((c, n))
    rng.shuffle(walls)
    parent = list(range(count))

    def find(r: int) -> int:
        while parent[r] != r:
            parent[r] = parent[parent[r]]
            r = parent[r]
        return r

    for a, b in walls:
        ra, rb = find(region_of[a]), find(region_of[b])
        if ra != rb:
            parent[ra] = rb
            grid.carve(a, b)
            yield Weld(a, b)


def choose_generator(grid: Grid, rng: random.Random) -> tuple[int, Iterator[GenEvent]]:
    """Pick a growth style at random. Returns (region count, event iterator)."""
    if rng.random() < 0.5:
        return 1, single_snake(grid, rng)
    heads = min(rng.randint(2, 4), grid.cols * grid.rows)
    return heads, multi_snake(grid, rng, heads)
