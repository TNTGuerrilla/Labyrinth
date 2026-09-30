"""The game's screensaver mode: the chosen screensaver solver's moves, as the cells the
dot follows. Pure logic with no pygame dependency."""
from __future__ import annotations

import random

from maze_saver.maze import Cell, Grid
from maze_saver.solver import Advance, Backtrack, solve_with


def solver_cells(grid: Grid, start: Cell, end: Cell, solver: str, lookahead: int,
                 rng: random.Random) -> list[Cell]:
    """Every cell the dot moves to, in order, not counting start. A backtrack is a step
    back along the trail, which the game's Trail draws as backed out of."""
    return [e.b for e in solve_with(solver, grid, start, end, rng, lookahead=lookahead)
            if isinstance(e, (Advance, Backtrack))]
