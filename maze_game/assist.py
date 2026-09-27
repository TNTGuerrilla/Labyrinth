"""Route finding for hints, the perfect step count and the win pulse."""
from __future__ import annotations

from collections import deque

from maze_saver.maze import Cell, Grid


def route(grid: Grid, a: Cell, b: Cell) -> list[Cell]:
    """Cells from a to b inclusive along open passages, or [] if b is unreachable."""
    parent: dict[Cell, Cell | None] = {a: None}
    queue = deque([a])
    while queue:
        cur = queue.popleft()
        if cur == b:
            break
        for n in grid.open_neighbors(cur):
            if n not in parent:
                parent[n] = cur
                queue.append(n)
    if b not in parent:
        return []
    path = [b]
    while parent[path[-1]] is not None:
        path.append(parent[path[-1]])
    return path[::-1]


def perfect_steps(grid: Grid, start: Cell, end: Cell) -> int:
    return max(0, len(route(grid, start, end)) - 1)


def hint_cells(grid: Grid, cell: Cell, end: Cell, length: int) -> list[Cell]:
    """The next `length` cells on the way from `cell` to `end`."""
    return route(grid, cell, end)[1:1 + length]


def toward_end(grid: Grid, end: Cell) -> dict[Cell, Cell]:
    """BFS from end over open passages: toward_end[c] is the neighbor one step closer to
    end. Lets Round build one parent map per maze instead of a fresh BFS per hint press."""
    parents: dict[Cell, Cell] = {}
    visited = {end}
    queue = deque([end])
    while queue:
        cur = queue.popleft()
        for n in grid.open_neighbors(cur):
            if n not in visited:
                visited.add(n)
                parents[n] = cur
                queue.append(n)
    return parents
