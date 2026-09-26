"""Human-like maze solver: lookahead pruning, occasional mistakes, bounded detours.

The dot walks a DFS stack like a person tracing a maze with a finger. It can see a
short distance down each branch (LOOKAHEAD cells) and will not wander into a branch
that visibly dead-ends within that distance. At a fork on the true route it usually
takes the correct turn, but sometimes (MISTAKE_CHANCE) takes a wrong one anyway and
wanders for a while before giving up and backing out, bounded by a random detour
budget (DETOUR_MIN..DETOUR_MAX steps).
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Iterator, Optional, Union

from .maze import Cell, Grid

LOOKAHEAD = 3
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


def _is_visible_dead_end(grid: Grid, c: Cell, n: Cell, end: Cell) -> bool:
    """True if a depth-limited walk from n (never back through c) exhausts within
    LOOKAHEAD steps of n without reaching end."""
    if n == end:
        return False
    visited = {c, n}
    frontier = {n}
    for _ in range(LOOKAHEAD):
        next_frontier = set()
        for cell in frontier:
            for nb in grid.open_neighbors(cell):
                if nb in visited:
                    continue
                visited.add(nb)
                if nb == end:
                    return False
                next_frontier.add(nb)
        frontier = next_frontier
        if not frontier:
            return True
    # frontier now holds the cells exactly LOOKAHEAD steps from n; if any still has an
    # unexplored neighbor, the branch continues deeper than we can see.
    for cell in frontier:
        for nb in grid.open_neighbors(cell):
            if nb not in visited:
                return False
    return True


def _candidates(grid: Grid, cur: Cell, visited: set, end: Cell) -> list[Cell]:
    return [n for n in grid.open_neighbors(cur)
            if n not in visited and not _is_visible_dead_end(grid, cur, n, end)]


def _choose_next(cur: Cell, candidates: list[Cell], on_path: set,
                  toward_end: dict[Cell, Cell], rng: random.Random) -> Cell:
    if cur not in on_path:
        return rng.choice(candidates)
    correct = toward_end.get(cur)
    if correct not in candidates:
        return rng.choice(candidates)
    others = [n for n in candidates if n != correct]
    if others and rng.random() < MISTAKE_CHANCE:
        return rng.choice(others)
    return correct


def solve(grid: Grid, start: Cell, end: Cell, rng: random.Random) -> Iterator[SolveEvent]:
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

        candidates = _candidates(grid, cur, visited, end)
        if candidates:
            nxt = _choose_next(cur, candidates, on_path, toward_end, rng)
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
