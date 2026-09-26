import random

import pytest

from maze_saver.maze import (E, N, W, Carve, Finish, Grid, Retreat, Start, Weld, choose_generator,
                             direction, edge_key, multi_snake, single_snake)
from tests.mazeutil import assert_perfect


def test_grid_basics():
    g = Grid(3, 2)
    assert g.neighbors((0, 0)) == [(1, 0), (0, 1)]
    assert not g.is_open((0, 0), (1, 0))
    g.carve((0, 0), (1, 0))
    assert g.is_open((1, 0), (0, 0))
    assert g.open_dirs((0, 0)) == E
    assert g.open_dirs((1, 0)) == W
    assert g.open_neighbors((1, 0)) == [(0, 0)]
    assert g.passage_count() == 1


def test_grid_rejects_bad_input():
    with pytest.raises(ValueError):
        Grid(0, 3)
    with pytest.raises(ValueError):
        Grid(3, 3).carve((0, 0), (1, 1))


def test_direction_and_edge_key():
    assert direction((1, 1), (1, 0)) == N
    assert edge_key((2, 0), (1, 0)) == ((1, 0), (2, 0))


@pytest.mark.parametrize("cols,rows", [(1, 1), (2, 1), (4, 4), (24, 38), (57, 24), (200, 200)])
def test_single_snake_is_perfect(cols, rows):
    for seed in range(5 if cols * rows < 2000 else 1):
        g = Grid(cols, rows)
        events = list(single_snake(g, random.Random(seed)))
        assert_perfect(g)
        assert isinstance(events[0], Start)
        assert isinstance(events[-1], Finish)
        assert sum(isinstance(e, Carve) for e in events) == cols * rows - 1


def test_single_snake_head_moves_one_cell_per_step():
    g = Grid(6, 6)
    head = None
    for e in single_snake(g, random.Random(3)):
        if isinstance(e, Start):
            head = e.cell
        elif isinstance(e, Carve):
            assert e.a == head
            head = e.b
        elif isinstance(e, Retreat):
            assert e.frm == head and g.is_open(e.frm, e.to)
            head = e.to
        elif isinstance(e, Finish):
            assert e.cell == head


@pytest.mark.parametrize("heads", [2, 3, 4])
@pytest.mark.parametrize("cols,rows", [(4, 4), (24, 38), (57, 24)])
def test_multi_snake_is_perfect(heads, cols, rows):
    for seed in range(5):
        g = Grid(cols, rows)
        events = list(multi_snake(g, random.Random(seed), heads))
        assert_perfect(g)
        starts = [e for e in events if isinstance(e, Start)]
        assert {e.region for e in starts} == set(range(heads))
        assert sum(isinstance(e, Weld) for e in events) == heads - 1
        owned = {e.cell for e in starts} | {e.b for e in events if isinstance(e, Carve)}
        assert len(owned) == cols * rows
        first_weld = next(i for i, e in enumerate(events) if isinstance(e, Weld))
        assert all(isinstance(e, Weld) for e in events[first_weld:])


def test_multi_snake_heads_take_turns():
    events = list(multi_snake(Grid(24, 38), random.Random(1), 3))
    assert [e.region for e in events[3:6]] == [0, 1, 2]


def test_multi_snake_clamps_heads_to_cell_count():
    g = Grid(1, 1)
    events = list(multi_snake(g, random.Random(0), 4))
    assert sum(isinstance(e, Start) for e in events) == 1
    assert_perfect(g)


def test_choose_generator_uses_both_styles():
    region_counts = set()
    for seed in range(40):
        g = Grid(8, 8)
        regions, events = choose_generator(g, random.Random(seed))
        starts = [e for e in events if isinstance(e, Start)]
        assert len(starts) == regions
        assert_perfect(g)
        region_counts.add(regions)
    assert 1 in region_counts
    assert region_counts & {2, 3, 4}


@pytest.mark.parametrize("cols,rows,expected_upper", [
    (12, 12, 4), (24, 38, 7), (40, 60, 12), (98, 40, 12),
])
def test_choose_generator_scales_leads_with_board_size(cols, rows, expected_upper):
    region_counts = set()
    for seed in range(200):
        g = Grid(cols, rows)
        regions, events = choose_generator(g, random.Random(seed), max_heads=12)
        list(events)
        assert_perfect(g)
        if regions > 1:
            assert 2 <= regions <= expected_upper
        region_counts.add(regions)
    if cols * rows == 40 * 60:
        assert 1 in region_counts
        assert any(r >= 8 for r in region_counts)


def test_choose_generator_max_heads_caps_upper_bound():
    region_counts = set()
    for seed in range(200):
        g = Grid(40, 60)
        regions, events = choose_generator(g, random.Random(seed), max_heads=3)
        list(events)
        assert_perfect(g)
        region_counts.add(regions)
    assert max(region_counts) <= 3


def test_choose_generator_forced_heads_one_is_single_snake():
    for seed in range(20):
        g = Grid(24, 38)
        regions, events = choose_generator(g, random.Random(seed), forced_heads=1)
        starts = [e for e in list(events) if isinstance(e, Start)]
        assert regions == 1
        assert len(starts) == 1
        assert_perfect(g)


def test_choose_generator_forced_heads_multi():
    for seed in range(20):
        g = Grid(40, 60)
        regions, events = choose_generator(g, random.Random(seed), forced_heads=8)
        starts = [e for e in list(events) if isinstance(e, Start)]
        assert regions == 8
        assert len(starts) == 8
        assert_perfect(g)


def test_choose_generator_forced_heads_clamped_to_cell_count():
    g = Grid(2, 2)
    regions, events = choose_generator(g, random.Random(0), forced_heads=8)
    starts = [e for e in list(events) if isinstance(e, Start)]
    assert regions == 4
    assert len(starts) == 4
    assert_perfect(g)
