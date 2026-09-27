import random

from maze_game.difficulty import (DIFFICULTIES, MIN_CUSTOM, PRESETS, ceiling, grid_size,
                                  pick_short, size_range)


def test_presets_are_the_spec_ranges():
    assert PRESETS == {"small": (8, 12), "medium": (13, 24), "large": (25, 48), "xl": (49, 96)}
    assert DIFFICULTIES == ("small", "medium", "large", "xl", "custom")
    assert MIN_CUSTOM == 4


def test_ceiling_is_80_percent_of_the_short_side():
    assert ceiling(1920, 1040) == 832
    assert ceiling(3, 3) == 4


def test_size_range():
    assert size_range("large", 0, 0, 500) == (25, 48)
    assert size_range("custom", 90, 30, 500) == (30, 90)
    assert size_range("custom", 1, 99999, 500) == (4, 500)
    assert size_range("xl", 0, 0, 60) == (49, 60)
    assert size_range("xl", 0, 0, 20) == (20, 20)


def test_pick_short_covers_the_range():
    rng = random.Random(1)
    values = {pick_short("small", 0, 0, 1920, 1040, rng) for _ in range(300)}
    assert values == set(range(8, 13))


def test_grid_size_landscape_fills_the_aspect_ratio():
    assert grid_size(24, 1920, 1040) == (44, 24)


def test_grid_size_portrait():
    assert grid_size(10, 500, 1000) == (10, 20)


def test_grid_at_the_ceiling_has_at_least_one_pixel_per_cell():
    w, h = 1920, 1040
    cols, rows = grid_size(ceiling(w, h), w, h)
    assert cols <= w * 4 // 5 and rows <= h * 4 // 5
