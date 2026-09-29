"""Windows-only checks of the preview against a hidden fake Screen Saver Settings window."""
import os
import sys

import pytest

if sys.platform != "win32":
    pytest.skip("Windows only", allow_module_level=True)

from maze_saver import monitors  # noqa: E402
from maze_saver.app import PreviewClaim, run_preview  # noqa: E402
from maze_saver.config import Settings  # noqa: E402

FAST = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500, hold_seconds=10)
MAX_FRAMES = 200  # bound so a broken exit check fails the test instead of hanging it


@pytest.fixture
def parent(monkeypatch):
    """A hidden top-level window standing in for Windows' preview box. SDL's real Windows
    driver attaches to our child in it (the dummy driver cannot adopt a native window);
    nothing shows because the parent is never made visible."""
    monkeypatch.setenv("SDL_VIDEODRIVER", "windows")
    hwnd = monitors.user32.CreateWindowExW(0, "STATIC", "fake preview", 0, 0, 0, 152, 112,
                                           None, None, None, None)
    assert hwnd
    yield hwnd
    monitors.destroy_window(hwnd)


def test_child_window_fills_the_parent(parent):
    child = monitors.create_preview_child(parent)
    try:
        assert monitors.is_window(child)
        assert monitors.get_parent(child) == parent
        assert monitors.client_size(child) == monitors.client_size(parent)
    finally:
        monitors.destroy_window(child)
    assert not monitors.is_window(child)


def test_child_is_not_created_for_a_missing_parent():
    assert monitors.create_preview_child(0) == 0


def test_shared_slot_is_shared_by_name():
    name = f"Local\\LabyrinthTestSlot-{os.getpid()}"
    a, b = monitors.SharedSlot(name), monitors.SharedSlot(name)
    try:
        assert a.value == 0
        a.value = 0x1234_5678_9ABC_DEF0
        assert b.value == 0x1234_5678_9ABC_DEF0
    finally:
        a.close()
        b.close()


def test_newest_claim_on_a_preview_window_wins(parent):
    other = parent + 4  # a different preview window id; the slot is keyed by number only
    first = PreviewClaim(parent)
    unrelated = PreviewClaim(other)
    try:
        assert not first.superseded()
        second = PreviewClaim(parent)
        try:
            assert first.superseded()
            assert not second.superseded()
            assert not unrelated.superseded()
        finally:
            second.close()
    finally:
        first.close()
        unrelated.close()


def test_preview_ends_when_the_child_is_destroyed(parent):
    seen = {}

    def on_frame(frame, child):
        seen.setdefault("child", child)
        assert monitors.get_parent(child) == parent
        if frame == 3:
            monitors.user32.DestroyWindow(child)

    frames = run_preview(parent, FAST, max_frames=MAX_FRAMES, on_frame=on_frame)
    assert 3 <= frames <= 5
    assert not monitors.is_window(seen["child"])
    assert monitors.is_window(parent)


def test_preview_ends_when_a_newer_preview_claims_the_window(parent):
    newer = []

    def on_frame(frame, child):
        if frame == 3:
            newer.append(PreviewClaim(parent))

    try:
        frames = run_preview(parent, FAST, max_frames=MAX_FRAMES, on_frame=on_frame)
    finally:
        for claim in newer:
            claim.close()
    assert 3 <= frames <= 5


def test_preview_ends_when_the_parent_is_destroyed(parent):
    def on_frame(frame, child):
        if frame == 3:
            monitors.user32.DestroyWindow(parent)

    frames = run_preview(parent, FAST, max_frames=MAX_FRAMES, on_frame=on_frame)
    assert 3 <= frames <= 5


def test_preview_runs_until_the_frame_limit_and_cleans_up(parent):
    children = []
    before = os.environ.get("SDL_WINDOWID")
    frames = run_preview(parent, FAST, max_frames=6, on_frame=lambda f, c: children.append(c))
    assert frames == 6
    assert not monitors.is_window(children[0])  # our child is destroyed on exit
    assert os.environ.get("SDL_WINDOWID") == before


def test_preview_does_nothing_without_a_parent():
    assert run_preview(0, FAST, max_frames=MAX_FRAMES) == 0


def test_preview_ends_when_the_child_is_asked_to_close(parent):
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.WinDLL("user32")
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    wm_close = 0x0010

    def on_frame(frame, child):
        if frame == 3:
            assert user32.PostMessageW(child, wm_close, 0, 0)

    frames = run_preview(parent, FAST, max_frames=MAX_FRAMES, on_frame=on_frame)
    assert 3 <= frames <= 5
