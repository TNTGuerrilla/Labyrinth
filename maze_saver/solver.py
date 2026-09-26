"""Depth-first maze solver that yields one event per animation step."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterator, Union

from .maze import Cell, Grid

GOAL_NOISE = 2.0  # random noise added to the distance score at each fork


@dataclass(frozen=True)
class Advance:
    a: Cell
    b: Cell


@dataclass(frozen=True)
class Backtrack:
    a: Cell
    b: Cell


@dataclass(frozen=True)
class Solved:
    path: tuple[Cell, ...]


SolveEvent = Union[Advance, Backtrack, Solved]


def solve(grid: Grid, start: Cell, end: Cell, rng: random.Random) -> Iterator[SolveEvent]:
    """DFS with a mild, noisy pull toward the goal so it still takes wrong turns."""
    if start == end:
        yield Solved((start,))
        return

    def ordered(c: Cell, visited: set) -> list[Cell]:
        options = [n for n in grid.open_neighbors(c) if n not in visited]
        return sorted(options,
                      key=lambda n: abs(n[0] - end[0]) + abs(n[1] - end[1]) + rng.random() * GOAL_NOISE)

    visited = {start}
    stack = [start]
    pending = [ordered(start, visited)]
    while stack:
        cur = stack[-1]
        options = pending[-1]
        nxt = None
        while options:
            candidate = options.pop(0)
            if candidate not in visited:
                nxt = candidate
                break
        if nxt is not None:
            visited.add(nxt)
            stack.append(nxt)
            pending.append(ordered(nxt, visited))
            yield Advance(cur, nxt)
            if nxt == end:
                yield Solved(tuple(stack))
                return
        else:
            stack.pop()
            pending.pop()
            if not stack:
                return
            yield Backtrack(cur, stack[-1])
