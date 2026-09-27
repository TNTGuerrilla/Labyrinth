"""Shared helpers for maze_game tests."""
import random

from maze_game.config import GameSettings
from maze_game.round import Phase, Round
from maze_saver.maze import Grid


def fork_grid():
    """A 3x2 perfect maze:

        (0,0)-(1,0)-(2,0)
          |     |     |
        (0,1) (1,1) (2,1)

    (1,0) is a fork, (0,0) and (2,0) are bends, the bottom row are dead ends.
    """
    grid = Grid(3, 2)
    for a, b in (((0, 0), (1, 0)), ((1, 0), (2, 0)), ((1, 0), (1, 1)),
                 ((0, 0), (0, 1)), ((2, 0), (2, 1))):
        grid.carve(a, b)
    return grid


FAST = GameSettings(gen_speed=1000)


def grown(cols=6, rows=4, settings=FAST, seed=1):
    """A round whose maze has finished growing."""
    r = Round(cols, rows, settings, random.Random(seed))
    for _ in range(100000):
        if r.phase is Phase.PLAY:
            return r
        r.update(1 / 60)
    raise AssertionError("growth never finished")
