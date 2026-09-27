import pytest

from maze_game.camera import Camera


def test_fit_fills_80_percent():
    c = Camera(20, 10, 1000, 500)
    assert c.fit_px == 40 and c.cell_px == 40 and c.zoom == 1.0 and not c.zoomed


def test_centered_at_fit():
    c = Camera(20, 10, 1000, 500)
    assert c.origin() == (100, 50)
    assert c.cell_rect((0, 0)) == (100, 50, 40, 40)
    assert c.to_cells(100, 50) == (0.0, 0.0)


def test_zoom_limits():
    c = Camera(20, 10, 1000, 500)
    c.zoom_by(100, (10, 5))
    assert c.cell_px == 48
    c.zoom_by(-100, (10, 5))
    assert c.cell_px == 40


def test_max_zoom_never_below_fit():
    c = Camera(2, 2, 1000, 1000)
    assert c.fit_px == 400
    c.zoom_by(5, (1, 1))
    assert c.cell_px == 400 and c.max_px == 400


def test_zoom_keeps_the_anchor_in_place():
    c = Camera(200, 100, 1000, 500)
    anchor = (37.5, 20.5)
    before = c.to_screen(*anchor)
    c.zoom_by(3, anchor)
    assert c.cell_px == 8
    assert c.to_screen(*anchor) == pytest.approx(before, abs=1.0)


def test_zooming_back_to_fit_recenters():
    c = Camera(200, 100, 1000, 500)
    c.zoom_by(3, (37.5, 20.5))
    c.zoom_by(-10, (37.5, 20.5))
    assert (c.cx, c.cy) == (100, 50)
    c.zoom_by(3, (37.5, 20.5))
    c.reset_zoom()
    assert not c.zoomed and (c.cx, c.cy) == (100, 50)


def test_follow_keeps_the_dot_in_the_central_zone():
    c = Camera(200, 100, 1000, 500)
    c.zoom_by(100, (100, 50))
    for _ in range(50):
        c.follow((160, 50), 0.1)
    sx, _ = c.to_screen(160, 50)
    assert 300 - 1 <= sx <= 700 + 1


def test_follow_does_nothing_at_fit():
    c = Camera(20, 10, 1000, 500)
    c.follow((0.5, 0.5), 1.0)
    assert c.origin() == (100, 50)


def test_resize_keeps_the_zoom_ratio():
    c = Camera(100, 50, 1000, 500)
    c.zoom_by(1, (50, 25))
    assert c.cell_px == 10
    c.resize(2000, 1000)
    assert c.fit_px == 16 and c.cell_px == 20


def test_cells_in_rect():
    c = Camera(20, 10, 1000, 500)
    assert c.cells_in_rect(0, 0, 1000, 500) == (0, 0, 20, 10)
    assert c.cells_in_rect(100, 50, 40, 40) == (0, 0, 1, 1)
    x0, y0, x1, y1 = c.cells_in_rect(0, 0, 50, 50)
    assert list(range(x0, x1)) == [] and list(range(y0, y1)) == []
    assert len(list(c.visible_cells())) == 200
