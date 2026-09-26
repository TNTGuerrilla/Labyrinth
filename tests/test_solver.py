import random

from maze_saver.maze import Grid, edge_key, multi_snake, single_snake
from maze_saver.solver import Advance, Backtrack, Solved, solve
from tests.mazeutil import bfs_path


def make_maze(cols, rows, seed):
    g = Grid(cols, rows)
    for _ in single_snake(g, random.Random(seed)):
        pass
    return g


def test_finds_the_unique_path():
    for seed in range(20):
        g = make_maze(12, 9, seed)
        events = list(solve(g, (0, 0), (11, 8), random.Random(seed + 100)))
        assert isinstance(events[-1], Solved)
        assert not any(isinstance(e, Solved) for e in events[:-1])
        assert list(events[-1].path) == bfs_path(g, (0, 0), (11, 8))


def test_moves_are_contiguous_through_open_walls():
    g = make_maze(10, 10, 7)
    pos = (3, 4)
    for e in list(solve(g, (3, 4), (9, 0), random.Random(1)))[:-1]:
        assert isinstance(e, (Advance, Backtrack))
        assert e.a == pos and g.is_open(e.a, e.b)
        pos = e.b
    assert pos == (9, 0)


def test_bright_trail_equals_true_path():
    g = make_maze(15, 11, 2)
    trail = {}
    events = list(solve(g, (0, 5), (14, 5), random.Random(9)))
    for e in events[:-1]:
        trail[edge_key(e.a, e.b)] = isinstance(e, Advance)
    path = events[-1].path
    bright = {k for k, v in trail.items() if v}
    assert bright == {edge_key(path[i], path[i + 1]) for i in range(len(path) - 1)}


def test_start_equals_end():
    g = make_maze(3, 3, 0)
    assert list(solve(g, (1, 1), (1, 1), random.Random(0))) == [Solved(((1, 1),))]


def test_works_on_multi_snake_mazes():
    g = Grid(20, 15)
    for _ in multi_snake(g, random.Random(4), 3):
        pass
    events = list(solve(g, (0, 0), (19, 14), random.Random(4)))
    assert list(events[-1].path) == bfs_path(g, (0, 0), (19, 14))


def test_sometimes_takes_wrong_turns():
    backtracks = 0
    for seed in range(20):
        g = make_maze(12, 12, seed)
        backtracks += sum(isinstance(e, Backtrack) for e in solve(g, (0, 0), (11, 11), random.Random(seed)))
    assert backtracks > 0
