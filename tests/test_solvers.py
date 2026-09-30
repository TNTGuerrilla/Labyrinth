import random

import pytest

from maze_saver.maze import Grid, single_snake
from maze_saver.solver import (DEFAULT_SOLVER, SOLVER_LABELS, SOLVERS, Advance, Backtrack,
                               Solved, _scan_branch, solve_with)
from tests.mazeutil import bfs_path


def make_maze(cols, rows, seed):
    g = Grid(cols, rows)
    for _ in single_snake(g, random.Random(seed)):
        pass
    return g


def fork_maze():
    """3x2:  (0,0)-(1,0)-(2,0)
               |     |     |
             (0,1) (1,1) (2,1)
    (1,1) is a dead end off the fork at (1,0)."""
    g = Grid(3, 2)
    for a, b in (((0, 0), (1, 0)), ((1, 0), (2, 0)), ((1, 0), (1, 1)),
                 ((0, 0), (0, 1)), ((2, 0), (2, 1))):
        g.carve(a, b)
    return g


def replay(events, start):
    """Walks the events with a stack, checking each move, and returns the final stack."""
    stack = [start]
    for e in events:
        if isinstance(e, Advance):
            assert e.a == stack[-1]
            assert e.b not in stack
            stack.append(e.b)
        elif isinstance(e, Backtrack):
            assert e.a == stack[-1] and len(stack) >= 2 and e.b == stack[-2]
            stack.pop()
    return stack


def test_labels_and_default():
    assert list(SOLVER_LABELS) == ["human", "dfs", "wall", "perfect"]
    assert list(SOLVER_LABELS.values()) == ["Human-like", "Depth-first", "Wall follower",
                                            "Perfect"]
    assert DEFAULT_SOLVER == "human" and set(SOLVERS) == set(SOLVER_LABELS)


@pytest.mark.parametrize("name", list(SOLVER_LABELS))
@pytest.mark.parametrize("seed", range(12))
def test_every_solver_reaches_the_finish_through_open_passages(name, seed):
    g = make_maze(13, 9, seed)
    start, end = (0, seed % 9), (12, 8 - seed % 9)
    events = list(solve_with(name, g, start, end, random.Random(seed), lookahead=3))
    assert isinstance(events[-1], Solved)
    assert not any(isinstance(e, Solved) for e in events[:-1])
    for e in events[:-1]:
        assert g.is_open(e.a, e.b)
    stack = replay(events[:-1], start)
    assert stack[-1] == end
    assert list(events[-1].path) == stack == bfs_path(g, start, end)


@pytest.mark.parametrize("name", list(SOLVER_LABELS))
def test_start_equals_end(name):
    g = make_maze(4, 4, 1)
    assert list(solve_with(name, g, (2, 2), (2, 2), random.Random(1))) == [Solved(((2, 2),))]


@pytest.mark.parametrize("name", list(SOLVER_LABELS))
def test_a_walled_in_start_gives_up_without_solving(name):
    g = Grid(2, 1)  # no passages
    events = list(solve_with(name, g, (0, 0), (1, 0), random.Random(1)))
    assert not any(isinstance(e, Solved) for e in events)


def test_unknown_name_uses_the_human_like_solver():
    g = make_maze(10, 8, 3)
    a = list(solve_with("nope", g, (0, 0), (9, 7), random.Random(5)))
    b = list(solve_with("human", g, (0, 0), (9, 7), random.Random(5)))
    assert a == b


def test_perfect_walks_the_shortest_route_only():
    g = make_maze(15, 11, 4)
    route = bfs_path(g, (0, 0), (14, 10))
    events = list(solve_with("perfect", g, (0, 0), (14, 10), random.Random(1)))
    assert events[:-1] == [Advance(a, b) for a, b in zip(route, route[1:])]


def test_wall_follower_keeps_its_left_hand_on_the_wall():
    g = fork_maze()
    events = list(solve_with("wall", g, (2, 1), (0, 1), random.Random(1)))
    assert events == [
        Advance((2, 1), (2, 0)),
        Advance((2, 0), (1, 0)),
        Advance((1, 0), (1, 1)),
        Backtrack((1, 1), (1, 0)),
        Advance((1, 0), (0, 0)),
        Advance((0, 0), (0, 1)),
        Solved(((2, 1), (2, 0), (1, 0), (0, 0), (0, 1))),
    ]


def test_wall_follower_ignores_the_lookahead():
    g = make_maze(12, 9, 6)
    a = list(solve_with("wall", g, (0, 0), (11, 8), random.Random(1), lookahead=0))
    b = list(solve_with("wall", g, (0, 0), (11, 8), random.Random(2), lookahead=12))
    assert a == b


def test_depth_first_skips_a_dead_end_it_can_see():
    g = fork_maze()
    events = list(solve_with("dfs", g, (2, 1), (0, 1), random.Random(1), lookahead=1))
    assert events == [
        Advance((2, 1), (2, 0)),
        Advance((2, 0), (1, 0)),
        Advance((1, 0), (0, 0)),
        Advance((0, 0), (0, 1)),
        Solved(((2, 1), (2, 0), (1, 0), (0, 0), (0, 1))),
    ]


@pytest.mark.parametrize("lookahead", [1, 3, 6])
@pytest.mark.parametrize("seed", range(8))
def test_depth_first_never_enters_a_visible_dead_end(lookahead, seed):
    g = make_maze(14, 10, seed)
    end = (13, 9)
    for e in solve_with("dfs", g, (0, 0), end, random.Random(seed), lookahead=lookahead):
        if isinstance(e, Advance):
            dead_end, _ = _scan_branch(g, e.a, e.b, end, lookahead)
            assert not dead_end


def trap_maze(width=45):
    """A wrong branch that looks closer to the finish: from the start (0, 2) the corridor
    east along row 2 ends at (width - 2, 2), one cell short of the finish (width - 1, 2).
    The real route goes up to row 0, east, and back down."""
    g = Grid(width, 3)
    for x in range(width - 2):
        g.carve((x, 2), (x + 1, 2))
    g.carve((0, 2), (0, 1))
    g.carve((0, 1), (0, 0))
    for x in range(width - 1):
        g.carve((x, 0), (x + 1, 0))
    g.carve((width - 1, 0), (width - 1, 1))
    g.carve((width - 1, 1), (width - 1, 2))
    return g


def test_depth_first_has_no_detour_limit():
    """It follows the tempting wrong branch all the way (43 cells, more than Human-like's
    DETOUR_MAX of 40) before backing out of it in one run."""
    g = trap_maze()
    events = list(solve_with("dfs", g, (0, 2), (44, 2), random.Random(1), lookahead=0))
    assert events[:43] == [Advance((x, 2), (x + 1, 2)) for x in range(43)]
    assert events[43:86] == [Backtrack((x + 1, 2), (x, 2)) for x in reversed(range(43))]
    assert events[86] == Advance((0, 2), (0, 1))
    assert isinstance(events[-1], Solved)
