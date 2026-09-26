import ctypes
import os
import sys

import pytest

if sys.platform != "win32":
    pytest.skip("Windows only", allow_module_level=True)

from maze_saver import monitors  # noqa: E402


def test_struct_sizes_match_win32():
    assert ctypes.sizeof(monitors.DEVMODEW) == 220
    assert ctypes.sizeof(monitors.MONITORINFOEXW) == 104


def test_get_monitors_reports_real_displays():
    monitors.enable_dpi_awareness()
    found = monitors.get_monitors()
    assert found
    assert all(m.w > 0 and m.h > 0 and m.hz >= 0 and m.dpi > 0 for m in found)
    assert found == sorted(found, key=lambda m: (m.x, m.y))
    assert any(m.x == 0 and m.y == 0 for m in found)  # the primary monitor


def test_cursor_pos_is_two_ints():
    x, y = monitors.cursor_pos()
    assert isinstance(x, int) and isinstance(y, int)


def test_is_window_rejects_null():
    assert not monitors.is_window(0)


def test_single_instance_mutex():
    name = f"Local\\MazeScreensaverTest{os.getpid()}"
    first = monitors.acquire_single_instance(name)
    assert first is not None
    assert monitors.acquire_single_instance(name) is None
    monitors.release_handle(first)
    again = monitors.acquire_single_instance(name)
    assert again is not None
    monitors.release_handle(again)
