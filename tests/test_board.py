import random

import pytest

from maze_saver.board import (MAX_STEPS_PER_FRAME, MIN_CELL_PX, StepAccumulator, choose_endpoints,
                              compute_geometry, fill)

MONITOR_SIZES = [(3440, 1440), (1200, 1920), (1920, 1200), (1920, 1080), (5120, 1440),
                 (3840, 2160), (1080, 1920), (1440, 2560), (800, 600), (1000, 1000)]


class FixedRng:
    """Returns preset randint values and records the bounds it was asked for."""

    def __init__(self, values):
        self.values = list(values)
        self.calls = []

    def randint(self, a, b):
        self.calls.append((a, b))
        value = self.values.pop(0)
        assert a <= value <= b
        return value


def split(w, h, g):
    """(n_short, n_long) for a geometry on a w x h monitor."""
    return (g.rows, g.cols) if w >= h else (g.cols, g.rows)


def check_geometry(w, h, g, coverage=100):
    n_short, n_long = split(w, h, g)
    short_fill, long_fill = fill(min(w, h), coverage), fill(max(w, h), coverage)
    assert g.cell >= 1
    assert n_short * g.cell <= short_fill
    assert short_fill // n_short == g.cell  # largest whole-pixel cell that fits
    assert n_short <= n_long
    assert n_long * g.cell <= long_fill
    assert g.x == (w - g.width) // 2 and g.y == (h - g.height) // 2
    assert g.x >= 0 and g.y >= 0


@pytest.mark.parametrize("w,h", MONITOR_SIZES)
def test_geometry_rules_hold(w, h):
    rng = random.Random(w * 7 + h)
    for _ in range(200):
        g = compute_geometry(w, h, 12, 40, rng)
        check_geometry(w, h, g)
        assert g.cell >= MIN_CELL_PX
        assert 12 <= split(w, h, g)[0] <= 40


def test_example_layout_values():
    rng = FixedRng([24, 57])
    g = compute_geometry(3440, 1440, 12, 40, rng, coverage=80)
    assert (g.cell, g.cols, g.rows) == (48, 57, 24)
    assert rng.calls == [(12, 40), (24, 57)]

    rng = FixedRng([24, 38])
    g = compute_geometry(1200, 1920, 12, 40, rng, coverage=80)
    assert (g.cell, g.cols, g.rows) == (40, 24, 38)
    assert rng.calls[1] == (24, 38)

    g = compute_geometry(1920, 1200, 12, 40, FixedRng([24, 38]), coverage=80)
    assert (g.cell, g.cols, g.rows) == (40, 38, 24)


def test_preview_box_clamps_to_min_cell():
    g = compute_geometry(152, 112, 40, 40, random.Random(1), coverage=80)
    assert (g.rows, g.cell) == (22, 4)
    check_geometry(152, 112, g, coverage=80)


def test_fill_takes_the_coverage_percent_rounded_down():
    assert fill(1440) == fill(1440, 100) == 1440
    assert fill(1440, 50) == 720
    assert fill(1080, 85) == 918
    assert fill(1081, 50) == 540


@pytest.mark.parametrize("coverage", [100, 50])
def test_geometry_short_side_fills_the_coverage(coverage):
    # 24 rows of a 1440 px short side: the cell is the coverage share over 24, rounded down.
    rng = FixedRng([24, 24])
    g = compute_geometry(3440, 1440, 12, 40, rng, coverage=coverage)
    short = 1440 * coverage // 100
    assert g.rows == 24 and g.cell == short // 24
    assert rng.calls[1] == (24, 3440 * coverage // 100 // g.cell)
    check_geometry(3440, 1440, g, coverage=coverage)


@pytest.mark.parametrize("coverage", [100, 50])
@pytest.mark.parametrize("w,h", MONITOR_SIZES)
def test_geometry_rules_hold_at_each_coverage(w, h, coverage):
    rng = random.Random(w * 3 + h + coverage)
    for _ in range(50):
        check_geometry(w, h, compute_geometry(w, h, 12, 40, rng, coverage=coverage), coverage)


def test_square_monitor_gives_square_board():
    g = compute_geometry(1000, 1000, 12, 40, random.Random(3))
    assert g.cols == g.rows


def test_tiny_monitor_still_valid():
    for w, h in [(10, 10), (3, 3), (40, 12)]:
        g = compute_geometry(w, h, 12, 40, random.Random(0), coverage=80)
        assert min(g.cols, g.rows) == 2
        assert g.width <= w and g.height <= h


@pytest.mark.parametrize("cols,rows", [(2, 2), (4, 4), (57, 24), (24, 38), (3, 50)])
def test_endpoints_far_apart(cols, rows):
    for seed in range(300):
        a, b = choose_endpoints(cols, rows, random.Random(seed))
        assert 0 <= a[0] < cols and 0 <= a[1] < rows
        assert 0 <= b[0] < cols and 0 <= b[1] < rows
        assert abs(a[0] - b[0]) + abs(a[1] - b[1]) >= (cols + rows) // 2


def test_endpoints_fall_back_to_corners():
    class ZeroRng:
        def randrange(self, n):
            return 0

    assert choose_endpoints(8, 5, ZeroRng()) == ((0, 0), (7, 4))


def test_accumulator_keeps_fractions():
    acc = StepAccumulator(2.5)
    assert [acc.take(0.25) for _ in range(8)] == [0, 1, 0, 1, 1, 0, 1, 1]


def test_accumulator_fraction_is_progress_to_next_step():
    acc = StepAccumulator(4)
    acc.take(0.3)
    assert acc.fraction == pytest.approx(0.2)


def test_accumulator_caps_and_drops_backlog():
    acc = StepAccumulator(1000)
    assert acc.take(10.0) == MAX_STEPS_PER_FRAME
    assert acc.take(0.0) == 0
