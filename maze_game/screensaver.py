"""The game's screensaver mode: the chosen screensaver solver's moves, as the cells the
dot follows. Pure logic with no pygame dependency."""
from __future__ import annotations

import random
from typing import Iterator

from maze_saver.maze import Cell, Grid
from maze_saver.solver import Advance, Backtrack, solve_with


def iter_solver_cells(grid: Grid, start: Cell, end: Cell, solver: str, lookahead: int,
                      rng: random.Random) -> Iterator[Cell]:
    """Every cell the dot moves to, in order, not counting start, computed only as it is
    asked for (a big maze's solve would otherwise stall a frame). A backtrack is a step
    back along the trail, which the game's Trail draws as backed out of."""
    for e in solve_with(solver, grid, start, end, rng, lookahead=lookahead):
        if isinstance(e, (Advance, Backtrack)):
            yield e.b


def solver_cells(grid: Grid, start: Cell, end: Cell, solver: str, lookahead: int,
                 rng: random.Random) -> list[Cell]:
    """iter_solver_cells, all at once."""
    return list(iter_solver_cells(grid, start, end, solver, lookahead, rng))
