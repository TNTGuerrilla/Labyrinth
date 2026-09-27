import pytest

from maze_game.benchmark import build_seconds, build_text, find_recommended, median, score


def test_score_drops_the_slowest_tenth():
    assert score([1 / 100] * 9 + [1.0]) == pytest.approx(100.0)


def test_score_of_nothing_is_zero():
    assert score([]) == 0.0


def search(limit, ceiling=860, calls=None):
    def measure(n):
        if calls is not None:
            calls.append(n)
        return 100.0 if n <= limit else 30.0
    return find_recommended(measure, ceiling)


def test_doubles_then_bisects():
    calls = []
    result = search(500, calls=calls)
    assert calls[:4] == [96, 192, 384, 768]
    assert 496 <= result <= 500


def test_the_example_from_the_spec():
    calls = []
    search(300, calls=calls)
    assert calls[:4] == [96, 192, 384, 288]


def test_halves_when_96_fails():
    calls = []
    result = search(30, calls=calls)
    assert calls[:3] == [96, 48, 24]
    assert 26 <= result <= 30


def test_reaches_the_ceiling():
    calls = []
    assert search(10 ** 6, ceiling=500, calls=calls) == 500
    assert calls == [96, 192, 384, 500]


def test_small_ceiling_below_the_start():
    assert search(10 ** 6, ceiling=50) == 50


def test_nothing_passes():
    assert search(0) == 4


def test_on_step_sees_each_size():
    seen = []
    find_recommended(lambda n: 100.0, 200, on_step=seen.append)
    assert seen == [96, 192, 200]


def test_build_helpers():
    assert median([3.0, 1.0, 2.0]) == 2.0
    assert build_seconds(1000, 2e-6) == pytest.approx(0.002)
    assert build_text(0.05) == "Building is instant"
    assert build_text(3.24) == "Building takes about 3.2 s"
    assert build_text(42.4) == "Building takes about 42 s"
