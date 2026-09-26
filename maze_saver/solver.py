"""Human-like maze solver: lookahead pruning, occasional mistakes, bounded detours.

The dot walks a DFS stack like a person tracing a maze with a finger. It can see a
short distance down each branch (`lookahead` cells from the fork) and will not wander
into a branch that visibly dead-ends within that distance. At a fork on the true route
it always takes the correct turn if it can see the finish down that branch; otherwise
it usually takes the correct turn, but sometimes (MISTAKE_CHANCE) takes a wrong one
anyway and wanders for a while before giving up and backing out, bounded by a random
detour budget (DETOUR_MIN..DETOUR_MAX steps).
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Iterator, Optional, Union

from .maze import Cell, Grid

DEFAULT_LOOKAHEAD = 4
MISTAKE_CHANCE = 0.3
DETOUR_MIN = 10
DETOUR_MAX = 40


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


def _toward_end_map(grid: Grid, end: Cell) -> dict[Cell, Cell]:
    """BFS from end over open passages: toward_end[c] is the neighbor one step closer to end."""
    toward_end: dict[Cell, Cell] = {}
    visited = {end}
    queue = deque([end])
    while queue:
        cur = queue.popleft()
        for n in grid.open_neighbors(cur):
            if n not in visited:
                visited.add(n)
                toward_end[n] = cur
                queue.append(n)
    return toward_end

def _true_path_cells(start: Cell, toward_end: dict[Cell, Cell]) -> set:
    on_path = set()
    c: Optional[Cell] = start
    while c is not None:
        on_path.add(c)
        c = toward_end.get(c)
    return on_path


def _scan_branch(grid: Grid, c: Cell, n: Cell, end: Cell, lookahead: int) -> tuple[bool, bool]:
    """Depth-limited walk from n (never back through c), out to `lookahead` cells from c
    (n itself is distance 1). Returns (dead_end, finish_in_sight):
    - dead_end: the walk is fully exhausted with every reached cell at distance <= lookahead
      from c, and the branch does not contain end within that walk.
    - finish_in_sight: end is reachable from n without going back through c, at distance
      <= lookahead from c.
    lookahead <= 0 disables both: never a dead end, finish never in sight.
    """
    if lookahead <= 0:
        return False, False
    if n == end:
        return False, True
    visited = {c, n}
    frontier = {n}
    finish_in_sight = False
    for _ in range(lookahead - 1):
        next_frontier = set()
        for cell in frontier:
            for nb in grid.open_neighbors(cell):
                if nb in visited:
                    continue
                visited.add(nb)
                if nb == end:
                    finish_in_sight = True
                next_frontier.add(nb)
        frontier = next_frontier
        if not frontier:
            return not finish_in_sight, finish_in_sight
    # frontier now holds the cells exactly `lookahead` steps from c; if any still has an
    # unexplored neighbor, the branch continues deeper than we can see.
    dead_end = not finish_in_sight
    if dead_end:
        for cell in frontier:
            for nb in grid.open_neighbors(cell):
                if nb not in visited:
                    dead_end = False
                    break
            if not dead_end:
                break
    return dead_end, finish_in_sight


def _candidates(grid: Grid, cur: Cell, visited: set, end: Cell, lookahead: int) -> list[Cell]:
    result = []
    for n in grid.open_neighbors(cur):
        if n in visited:
            continue
        dead_end, _ = _scan_branch(grid, cur, n, end, lookahead)
        if not dead_end:
            result.append(n)
    return result


def _choose_next(grid: Grid, cur: Cell, candidates: list[Cell], on_path: set,
                  toward_end: dict[Cell, Cell], end: Cell, lookahead: int,
                  rng: random.Random) -> Cell:
    if cur not in on_path:
        return rng.choice(candidates)
    correct = toward_end.get(cur)
    if correct not in candidates:
        return rng.choice(candidates)
    _, finish_in_sight = _scan_branch(grid, cur, correct, end, lookahead)
    if finish_in_sight:
        return correct
    others = [n for n in candidates if n != correct]
    if others and rng.random() < MISTAKE_CHANCE:
        return rng.choice(others)
    return correct


def solve(grid: Grid, start: Cell, end: Cell, rng: random.Random,
          lookahead: int = DEFAULT_LOOKAHEAD) -> Iterator[SolveEvent]:
    """DFS that hugs the true route, occasionally detouring down a wrong branch."""
    if start == end:
        yield Solved((start,))
        return

    toward_end = _toward_end_map(grid, end)
    on_path = _true_path_cells(start, toward_end)

    visited = {start}
    stack = [start]
    fork_cell: Optional[Cell] = None
    budget = 0

    while True:
        cur = stack[-1]
        if cur == end:
            yield Solved(tuple(stack))
            return

        candidates = _candidates(grid, cur, visited, end, lookahead)
        if candidates:
            nxt = _choose_next(grid, cur, candidates, on_path, toward_end, end, lookahead, rng)
            entering_detour = fork_cell is None and cur in on_path and nxt not in on_path
            visited.add(nxt)
            stack.append(nxt)
            yield Advance(cur, nxt)
            if entering_detour:
                fork_cell = cur
                budget = rng.randint(DETOUR_MIN, DETOUR_MAX) - 1
            elif fork_cell is not None:
                budget -= 1
        else:
            if len(stack) == 1:
                return
            aband = stack.pop()
            yield Backtrack(aband, stack[-1])
            if fork_cell is not None:
                budget -= 1

        if fork_cell is not None and budget <= 0:
            while stack[-1] != fork_cell:
                aband = stack.pop()
                yield Backtrack(aband, stack[-1])
        if fork_cell is not None and stack[-1] == fork_cell:
            fork_cell = None
