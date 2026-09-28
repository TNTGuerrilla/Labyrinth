import sys
from pathlib import Path

import pytest

from labyrinth_update.elevate import command_line, run_elevated, schedule_delete_at_reboot
from labyrinth_update.net import UpdateError


def test_command_line_quotes_paths_with_spaces():
    line = command_line(["--apply-update", r"C:\Users\A B\u.exe", r"C:\Windows\x.scr", "ab"])
    assert line == '--apply-update "C:\\Users\\A B\\u.exe" C:\\Windows\\x.scr ab'


@pytest.mark.skipif(sys.platform == "win32", reason="elevation is real on Windows")
def test_elevation_is_windows_only(tmp_path):
    with pytest.raises(UpdateError):
        run_elevated(tmp_path / "x.exe", [])
    schedule_delete_at_reboot(Path(tmp_path / "x"))  # a quiet no-op
