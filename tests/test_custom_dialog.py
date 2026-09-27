import pygame
import pytest

from maze_game.ui.custom_dialog import CustomDialog


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def dialog(**kw):
    args = dict(cmin=20, cmax=40, ceiling=800, bench_size=None, bench_rate=None,
                view=(1920, 1040))
    args.update(kw)
    return CustomDialog(**args)


def test_initial_values_are_clamped():
    assert dialog(cmin=1, cmax=5000).values == [4, 800]


def test_arrows_step_and_switch_fields():
    d = dialog()
    d.handle("right", 0.0)
    assert d.values == [21, 40]
    d.handle("down", 1.0)
    d.handle("left", 2.0)
    assert d.values == [21, 39]


def test_holding_accelerates():
    d = dialog()
    for i in range(40):
        d.handle("right", i * 0.03)
    assert d.values[0] == 730


def test_typing_digits_and_backspace():
    d = dialog()
    for digit in "150":
        d.handle(f"digit:{digit}")
    assert d.values[0] == 150
    d.handle("backspace")
    assert d.values[0] == 15


def test_typed_values_are_clamped_when_committed():
    d = dialog()
    d.handle("digit:2")
    d.handle("down")
    assert d.values[0] == 4


def test_confirm_orders_min_and_max():
    d = dialog(cmin=90, cmax=30)
    assert d.handle("confirm") == "start"
    assert d.result() == (30, 90)


def test_cancel_closes():
    assert dialog().handle("cancel") == "close"


def test_notes_before_a_benchmark():
    lines = [line for line, _ in dialog().notes()]
    assert any("benchmark" in line for line in lines)


def test_notes_with_a_benchmark():
    lines = [line for line, _ in dialog(cmax=500, bench_size=300, bench_rate=2e-6).notes()]
    assert lines[0] == "Recommended max: 300"
    assert any(line.startswith("Above the recommended size") for line in lines)
    assert "Building takes about 0.9 s" in lines


def test_clicks():
    d = dialog()
    surface = pygame.Surface((1280, 720))
    d.draw(surface)
    assert d.click(d.hits.rect_for(("inc", 0)).center) is None
    assert d.values[0] == 21
    assert d.click(d.hits.rect_for("benchmark").center) == "benchmark"
    assert d.click(d.hits.rect_for("start").center) == "start"
    assert d.click(d.hits.rect_for("close").center) == "close"
