"""Shared helpers for maze_game tests."""
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
