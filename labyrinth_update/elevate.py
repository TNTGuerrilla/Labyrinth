"""Running a program with administrator rights (the UAC prompt) on Windows."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .net import UpdateError

ERROR_CANCELLED = 1223
MOVEFILE_DELAY_UNTIL_REBOOT = 0x4
SEE_MASK_CLASSNAME = 0x1
SEE_MASK_NOCLOSEPROCESS = 0x40
SEE_MASK_NOASYNC = 0x100
SW_HIDE = 0
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0
EXE_CLASS = "exefile"  # the registry class of .exe files


def command_line(args: Sequence[str]) -> str:
    """Arguments quoted the way Windows programs (and Python's sys.argv) split them."""
    return subprocess.list2cmdline(list(args))


def wait_for_exit_code(kernel32, process) -> int:
    """Wait for a started process and return its exit code. Raises UpdateError if Windows
    reports a failure, so a failed wait is never mistaken for success (exit code 0)."""
    import ctypes
    if kernel32.WaitForSingleObject(process, INFINITE) != WAIT_OBJECT_0:
        raise UpdateError("The update could not be installed.")
    code = ctypes.c_ulong()
    if not kernel32.GetExitCodeProcess(process, ctypes.byref(code)):
        raise UpdateError("The update could not be installed.")
    return code.value


def run_elevated(program: Path, args: Sequence[str]) -> int:
    """Run program through the UAC prompt and wait for it to finish. Returns its exit code.
    Raises UpdateError if the user says no or it cannot start. program is run as a program
    whatever its extension (a .scr included): the "exefile" class makes ShellExecuteEx
    ignore the file association, which other programs can claim for .scr.

    Known limitation, shared with most self-unpacking Windows programs: the elevated program
    is a Nuitka onefile build that unpacks into the user's %LOCALAPPDATA% cache, and HKCU
    can override the "exefile" class, so software already running as this user could get its
    own code run elevated when the user accepts the prompt. Microsoft does not treat UAC
    within one account as a security boundary. The README explains this under Updates."""
    if sys.platform != "win32":
        raise UpdateError("Administrator updates are only needed on Windows.")
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", ctypes.c_ulong),
                    ("hwnd", wintypes.HWND), ("lpVerb", wintypes.LPCWSTR),
                    ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int),
                    ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIconOrMonitor", wintypes.HANDLE),
                    ("hProcess", wintypes.HANDLE)]

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    shell32.ShellExecuteExW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_ulong)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC | SEE_MASK_CLASSNAME
    info.lpClass = EXE_CLASS
    info.lpVerb = "runas"
    info.lpFile = str(program)
    info.lpParameters = command_line(args)
    info.lpDirectory = str(program.parent)
    info.nShow = SW_HIDE
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        if ctypes.get_last_error() == ERROR_CANCELLED:
            raise UpdateError("Update needs administrator permission.")
        raise UpdateError("The updater could not start with administrator rights.")
    if not info.hProcess:
        raise UpdateError("The updater could not start with administrator rights.")
    try:
        return wait_for_exit_code(kernel32, info.hProcess)
    finally:
        kernel32.CloseHandle(info.hProcess)


def schedule_delete_at_reboot(path: Path) -> None:
    """Ask Windows to delete a file at the next restart. Needs administrator rights; quietly
    does nothing without them or on other systems."""
    if sys.platform != "win32":
        return
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.MoveFileExW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD]
    kernel32.MoveFileExW.restype = wintypes.BOOL
    kernel32.MoveFileExW(str(path), None, MOVEFILE_DELAY_UNTIL_REBOOT)
