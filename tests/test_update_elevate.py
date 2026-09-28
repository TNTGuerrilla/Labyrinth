import sys
from pathlib import Path

import pytest

from labyrinth_update.elevate import (command_line, run_elevated, schedule_delete_at_reboot,
                                      wait_for_exit_code)
from labyrinth_update.net import UpdateError


def test_command_line_quotes_paths_with_spaces():
    line = command_line(["--apply-update", r"C:\Users\A B\u.exe", r"C:\Windows\x.scr", "ab"])
    assert line == '--apply-update "C:\\Users\\A B\\u.exe" C:\\Windows\\x.scr ab'


@pytest.mark.skipif(sys.platform == "win32", reason="elevation is real on Windows")
def test_elevation_is_windows_only(tmp_path):
    with pytest.raises(UpdateError):
        run_elevated(tmp_path / "x.exe", [])
    schedule_delete_at_reboot(Path(tmp_path / "x"))  # a quiet no-op


class FakeKernel32:
    def __init__(self, wait=0, got=1, code=0):
        self.wait, self.got, self.code = wait, got, code

    def WaitForSingleObject(self, handle, timeout):
        return self.wait

    def GetExitCodeProcess(self, handle, code_ref):
        code_ref._obj.value = self.code
        return self.got


def test_wait_for_exit_code_returns_the_exit_code():
    assert wait_for_exit_code(FakeKernel32(code=2), 1) == 2


@pytest.mark.parametrize("kernel32", [FakeKernel32(wait=0xFFFFFFFF), FakeKernel32(wait=0x102),
                                      FakeKernel32(got=0)])
def test_wait_for_exit_code_treats_api_failures_as_failures(kernel32):
    with pytest.raises(UpdateError, match="could not be installed"):
        wait_for_exit_code(kernel32, 1)
