import random

import pytest

from maze_game.screensaver import iter_solver_cells, solver_cells
from maze_game.trail import Trail
from maze_saver.maze import Grid, single_snake
from tests.mazeutil import bfs_path


def make_maze(cols, rows, seed):
    g = Grid(cols, rows)
    for _ in single_snake(g, random.Random(seed)):
        pass
    return g


@pytest.mark.parametrize("solver", ["human", "dfs", "wall", "perfect"])
def test_cells_walk_to_the_end_one_step_at_a_time(solver):
    g = make_maze(12, 9, 3)
    cells = solver_cells(g, (0, 0), (11, 8), solver, 4, random.Random(2))
    assert cells[-1] == (11, 8)
    trail = Trail((0, 0))
    for c in cells:
        assert g.is_open(trail.cell, c)
        trail.move(trail.cell, c)
    assert trail.route == bfs_path(g, (0, 0), (11, 8))


def test_perfect_cells_are_the_route_after_the_start():
    g = make_maze(10, 7, 5)
    route = bfs_path(g, (0, 0), (9, 6))
    assert solver_cells(g, (0, 0), (9, 6), "perfect", 4, random.Random(1)) == route[1:]


def test_start_equals_end_gives_no_moves():
    g = make_maze(4, 4, 1)
    assert solver_cells(g, (1, 1), (1, 1), "wall", 4, random.Random(1)) == []


def test_iter_solver_cells_is_lazy_and_matches_the_list():
    g = make_maze(12, 9, 3)
    it = iter_solver_cells(g, (0, 0), (11, 8), "dfs", 4, random.Random(2))
    assert not isinstance(it, list) and iter(it) is it
    assert list(it) == solver_cells(g, (0, 0), (11, 8), "dfs", 4, random.Random(2))
