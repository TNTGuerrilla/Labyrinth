import random

from maze_saver.maze import Grid, edge_key, multi_snake, single_snake
from maze_saver.solver import DETOUR_MAX, LOOKAHEAD, Advance, Backtrack, Solved, solve
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
    wrong_advances = 0
    for seed in range(20):
        g = make_maze(12, 12, seed)
        start, end = (0, 0), (11, 11)
        on_path = set(bfs_path(g, start, end))
        events = list(solve(g, start, end, random.Random(seed)))
        wrong_advances += sum(isinstance(e, Advance) and e.b not in on_path for e in events)
    assert wrong_advances > 0


def _excursion_lengths(events, on_path):
    """Lengths of maximal runs of events touching a cell off the true path."""
    lengths = []
    current = 0
    for e in events:
        off_path = e.a not in on_path or e.b not in on_path
        if off_path:
            current += 1
        else:
            if current:
                lengths.append(current)
            current = 0
    if current:
        lengths.append(current)
    return lengths


def _branch_is_visible_dead_end(grid, c, n, end, lookahead=LOOKAHEAD):
    """Independent reimplementation of the solver's lookahead rule, for verification."""
    if n == end:
        return False
    visited = {c, n}
    frontier = {n}
    for _ in range(lookahead):
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
    for cell in frontier:
        for nb in grid.open_neighbors(cell):
            if nb not in visited:
                return False
    return True


def test_detours_are_bounded():
    max_excursion = 0
    for seed in range(30):
        g = make_maze(30, 20, seed)
        start, end = (0, 0), (29, 19)
        on_path = set(bfs_path(g, start, end))
        events = list(solve(g, start, end, random.Random(seed)))
        for length in _excursion_lengths(events[:-1], on_path):
            assert length <= 2 * DETOUR_MAX
            max_excursion = max(max_excursion, length)


def test_never_enters_a_visible_dead_end():
    for seed in range(20):
        g = make_maze(20, 15, seed)
        start, end = (0, 0), (19, 14)
        on_path = set(bfs_path(g, start, end))
        events = list(solve(g, start, end, random.Random(seed)))
        for e in events[:-1]:
            if isinstance(e, Advance) and e.b not in on_path:
                assert not _branch_is_visible_dead_end(g, e.a, e.b, end)


def test_long_mazes_finish_reasonably():
    max_ratio = 0.0
    for seed in range(20):
        g = make_maze(60, 40, seed)
        start, end = (0, 0), (59, 39)
        path_len = len(bfs_path(g, start, end))
        events = list(solve(g, start, end, random.Random(seed)))
        limit = 6 * path_len + 400
        assert len(events) < limit
        max_ratio = max(max_ratio, len(events) / path_len)
    print(f"max events/path ratio: {max_ratio:.3f}")


def test_deterministic_given_seed():
    g = make_maze(20, 15, 3)
    start, end = (0, 0), (19, 14)
    events_a = list(solve(g, start, end, random.Random(42)))
    events_b = list(solve(g, start, end, random.Random(42)))
    assert events_a == events_b
