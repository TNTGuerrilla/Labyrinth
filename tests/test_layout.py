import pytest

from maze_saver.layout import (Monitor, Rect, bounding_box, frame_cap, needs_multiwindow, plan_layout,
                               scale_to_fit)

EXAMPLE = [Monitor(-1200, -197, 1200, 1920, hz=60), Monitor(0, 0, 3440, 1440, hz=180),
           Monitor(3440, 139, 1920, 1200, hz=60)]

FIXTURES = {
    "single_1080p": [Monitor(0, 0, 1920, 1080)],
    "super_ultrawide": [Monitor(0, 0, 5120, 1440)],
    "example": EXAMPLE,
    "stacked": [Monitor(0, 0, 1920, 1080), Monitor(0, -1440, 2560, 1440)],
    "portrait_middle": [Monitor(-1920, 0, 1920, 1080), Monitor(0, -420, 1080, 1920),
                        Monitor(1080, 0, 1920, 1080)],
    "staggered_gaps": [Monitor(0, 0, 1920, 1080), Monitor(2200, 600, 1920, 1080)],
    "primary_right": [Monitor(-5120, 0, 2560, 1440), Monitor(-2560, 0, 2560, 1440),
                      Monitor(0, 0, 1920, 1080)],
    "mixed_dpi": [Monitor(0, 0, 3840, 2160, dpi=144), Monitor(3840, 0, 1920, 1080, dpi=96)],
    "mixed_hz": [Monitor(0, 0, 2560, 1440, hz=144), Monitor(2560, 0, 1920, 1080, hz=60)],
    "bogus_hz": [Monitor(0, 0, 1920, 1080, hz=1)],
    "spread": [Monitor(i * 1920, i * 1080, 1920, 1080) for i in range(4)],
    "huge": [Monitor(i * 7680, 0, 7680, 4320) for i in range(3)],
}
MULTI = {"spread", "huge"}


def test_rect_helpers():
    r = Rect(10, 20, 30, 40)
    assert (r.right, r.bottom, r.area) == (40, 60, 1200)
    assert r.moved(-10, 5) == Rect(0, 25, 30, 40)
    assert r.contains(Rect(10, 20, 30, 40)) and not r.contains(Rect(9, 20, 30, 40))


def test_bounding_box_of_example():
    assert bounding_box(EXAMPLE) == Rect(-1200, -197, 6560, 1920)


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_plan_layout(name):
    monitors = FIXTURES[name]
    layout = plan_layout(monitors, "auto")
    assert layout.multiwindow == (name in MULTI)
    assert layout.window == bounding_box(monitors)
    assert layout.boards == tuple(m.rect for m in monitors)
    assert all(layout.window.contains(b) for b in layout.boards)
    assert needs_multiwindow(monitors) == (name in MULTI)


def test_force_multiwindow():
    assert plan_layout(EXAMPLE, "auto", force_multiwindow=True).multiwindow


def test_no_monitors_is_an_error():
    with pytest.raises(ValueError):
        plan_layout([], "auto")


def test_frame_cap():
    assert frame_cap(EXAMPLE, "auto") == 180
    assert frame_cap(FIXTURES["mixed_hz"], "auto") == 144
    assert frame_cap(FIXTURES["bogus_hz"], "auto") == 60
    assert frame_cap([Monitor(0, 0, 10, 10, hz=0)], "auto") == 60
    assert frame_cap([Monitor(0, 0, 10, 10, hz=360)], "auto") == 240
    assert frame_cap([Monitor(0, 0, 10, 10, hz=24)], "auto") == 30
    assert frame_cap(EXAMPLE, 60) == 60
    assert frame_cap(EXAMPLE, 120) == 120


def test_scale_to_fit_example():
    (w, h), rects = scale_to_fit(EXAMPLE, 1600, 900)
    assert w <= 1600 and h <= 900 and w == 1600
    window = Rect(0, 0, w, h)
    assert len(rects) == 3
    assert all(window.contains(r) and r.w > 0 and r.h > 0 for r in rects)
    assert rects[0].x == 0
    assert rects[0].h > rects[0].w  # portrait stays portrait


def test_scale_to_fit_never_enlarges():
    size, rects = scale_to_fit([Monitor(0, 0, 800, 600)], 1600, 900)
    assert size == (800, 600) and rects == [Rect(0, 0, 800, 600)]
