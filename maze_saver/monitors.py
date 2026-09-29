"""Thin ctypes wrappers around the Win32 calls the screensaver needs."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from typing import Optional

from .layout import Monitor

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
try:
    shcore: Optional[ctypes.WinDLL] = ctypes.WinDLL("shcore")
except OSError:
    shcore = None

ENUM_CURRENT_SETTINGS = 0xFFFFFFFF
HWND_TOPMOST = -1
SWP_SHOWWINDOW = 0x0040
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
ERROR_ALREADY_EXISTS = 183
GWLP_HWNDPARENT = -8
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
PROCESS_PER_MONITOR_DPI_AWARE = 2
MDT_EFFECTIVE_DPI = 0
DEFAULT_DPI = 96
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_CMONITORS = 80
WS_CHILD = 0x40000000
WS_VISIBLE = 0x10000000
ERROR_CLASS_ALREADY_EXISTS = 1410
PREVIEW_CHILD_CLASS = "LabyrinthPreviewChild"
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1)
PAGE_READWRITE = 0x04
FILE_MAP_ALL_ACCESS = 0x000F001F


class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", wintypes.WCHAR * 32),
    ]


class DEVMODEW(ctypes.Structure):
    # Display variant of the DEVMODEW unions (dmPosition, dmDisplayFlags).
    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmPositionX", wintypes.LONG),
        ("dmPositionY", wintypes.LONG),
        ("dmDisplayOrientation", wintypes.DWORD),
        ("dmDisplayFixedOutput", wintypes.DWORD),
        ("dmColor", ctypes.c_short),
        ("dmDuplex", ctypes.c_short),
        ("dmYResolution", ctypes.c_short),
        ("dmTTOption", ctypes.c_short),
        ("dmCollate", ctypes.c_short),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
        ("dmICMMethod", wintypes.DWORD),
        ("dmICMIntent", wintypes.DWORD),
        ("dmMediaType", wintypes.DWORD),
        ("dmDitherType", wintypes.DWORD),
        ("dmReserved1", wintypes.DWORD),
        ("dmReserved2", wintypes.DWORD),
        ("dmPanningWidth", wintypes.DWORD),
        ("dmPanningHeight", wintypes.DWORD),
    ]


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), MONITORENUMPROC,
                                       wintypes.LPARAM]
user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFOEXW)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.EnumDisplaySettingsW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DEVMODEW)]
user32.EnumDisplaySettingsW.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
user32.SetWindowLongPtrW.restype = ctypes.c_void_p
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetParent.restype = wintypes.HWND
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.RegisterClassExW.restype = wintypes.ATOM
user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.HWND,
                                   wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.DestroyWindow.restype = wintypes.BOOL
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.CreateFileMappingW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                        wintypes.DWORD, wintypes.LPCWSTR]
kernel32.CreateFileMappingW.restype = wintypes.HANDLE
kernel32.MapViewOfFile.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                   ctypes.c_size_t]
kernel32.MapViewOfFile.restype = ctypes.c_void_p
kernel32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
kernel32.UnmapViewOfFile.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.SetPriorityClass.restype = wintypes.BOOL
if shcore is not None:
    shcore.GetDpiForMonitor.argtypes = [wintypes.HMONITOR, ctypes.c_int, ctypes.POINTER(wintypes.UINT),
                                        ctypes.POINTER(wintypes.UINT)]
    shcore.GetDpiForMonitor.restype = ctypes.c_long
    shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
    shcore.SetProcessDpiAwareness.restype = ctypes.c_long


def enable_dpi_awareness() -> None:
    """Per-monitor v2 so every coordinate is a physical pixel. Call before pygame.init()."""
    set_context = getattr(user32, "SetProcessDpiAwarenessContext", None)
    if set_context is not None:
        set_context.argtypes = [ctypes.c_void_p]
        set_context.restype = wintypes.BOOL
        if set_context(ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)):
            return
    if shcore is not None and shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE) == 0:
        return
    user32.SetProcessDPIAware()


def _dpi(hmonitor: int) -> int:
    if shcore is None:
        return DEFAULT_DPI
    x, y = wintypes.UINT(), wintypes.UINT()
    if shcore.GetDpiForMonitor(hmonitor, MDT_EFFECTIVE_DPI, ctypes.byref(x), ctypes.byref(y)) != 0:
        return DEFAULT_DPI
    return int(x.value)


def _refresh_rate(device: str) -> int:
    mode = DEVMODEW()
    mode.dmSize = ctypes.sizeof(DEVMODEW)
    if not user32.EnumDisplaySettingsW(device, ENUM_CURRENT_SETTINGS, ctypes.byref(mode)):
        return 0
    return int(mode.dmDisplayFrequency)


def get_monitors() -> list[Monitor]:
    handles: list[int] = []

    def on_monitor(hmonitor, hdc, rect, data):
        handles.append(hmonitor)
        return True

    callback = MONITORENUMPROC(on_monitor)  # keep a reference for the duration of the call
    user32.EnumDisplayMonitors(None, None, callback, 0)
    found = []
    for hmonitor in handles:
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if not user32.GetMonitorInfoW(hmonitor, ctypes.byref(info)):
            continue
        r = info.rcMonitor
        found.append(Monitor(r.left, r.top, r.right - r.left, r.bottom - r.top,
                             dpi=_dpi(hmonitor), hz=_refresh_rate(info.szDevice), name=info.szDevice))
    return sorted(found, key=lambda m: (m.x, m.y))


_last_cursor: Optional[tuple[int, int]] = None


def cursor_pos() -> tuple[int, int]:
    """Returns the cursor position, or the last known-good one if GetCursorPos fails
    (happens on the secure desktop / lock screen). Returns (0, 0) if it has never succeeded."""
    global _last_cursor
    point = wintypes.POINT()
    if user32.GetCursorPos(ctypes.byref(point)):
        _last_cursor = (int(point.x), int(point.y))
        return _last_cursor
    if _last_cursor is not None:
        return _last_cursor
    return (0, 0)


def virtual_screen_signature() -> tuple[int, int, int, int, int]:
    """Cheap snapshot of the virtual desktop's extent and monitor count, for detecting
    monitor changes without a full get_monitors() enumeration."""
    metrics = user32.GetSystemMetrics
    return (metrics(SM_XVIRTUALSCREEN), metrics(SM_YVIRTUALSCREEN), metrics(SM_CXVIRTUALSCREEN),
            metrics(SM_CYVIRTUALSCREEN), metrics(SM_CMONITORS))


def get_parent(hwnd: int) -> int:
    if not hwnd:
        return 0
    return user32.GetParent(hwnd) or 0


def set_topmost(hwnd: int, x: int, y: int, w: int, h: int) -> None:
    user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h, SWP_SHOWWINDOW)


def bring_to_foreground(hwnd: int) -> None:
    user32.SetForegroundWindow(hwnd)


def set_owner(hwnd: int, owner_hwnd: int) -> None:
    user32.SetWindowLongPtrW(hwnd, GWLP_HWNDPARENT, owner_hwnd)


def is_window(hwnd: int) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


def client_size(hwnd: int) -> tuple[int, int]:
    rect = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        return (0, 0)
    return (rect.right - rect.left, rect.bottom - rect.top)


_preview_class_registered = False


def _register_preview_class() -> bool:
    """Registers the preview child's window class once. Its window procedure is
    DefWindowProcW itself, so there is no Python callback to keep alive, and it has no
    background brush, so the window never paints over what SDL draws."""
    global _preview_class_registered
    if _preview_class_registered:
        return True
    wc = WNDCLASSEXW()
    wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
    wc.lpfnWndProc = ctypes.cast(user32.DefWindowProcW, ctypes.c_void_p).value
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.lpszClassName = PREVIEW_CHILD_CLASS
    ctypes.set_last_error(0)
    if not user32.RegisterClassExW(ctypes.byref(wc)) and ctypes.get_last_error() != ERROR_CLASS_ALREADY_EXISTS:
        return False
    _preview_class_registered = True
    return True


def create_preview_child(parent_hwnd: int) -> int:
    """Creates our own visible child window filling the parent's client area, the way a
    screensaver draws its preview. Returns the child hwnd, or 0 on failure."""
    if not is_window(parent_hwnd) or not _register_preview_class():
        return 0
    w, h = client_size(parent_hwnd)
    return user32.CreateWindowExW(0, PREVIEW_CHILD_CLASS, "Labyrinth preview", WS_CHILD | WS_VISIBLE,
                                  0, 0, max(1, w), max(1, h), parent_hwnd, None,
                                  kernel32.GetModuleHandleW(None), None) or 0


def destroy_window(hwnd: int) -> None:
    """Destroys a window this thread created, if it still exists."""
    if is_window(hwnd):
        user32.DestroyWindow(hwnd)


class SharedSlot:
    """One 64-bit value in a named, pagefile-backed file mapping, shared by every process
    in the session that opens the same name. It lives while any process holds it open.
    A process that cannot open it gets value 0 and writes that go nowhere."""

    def __init__(self, name: str) -> None:
        self._handle = kernel32.CreateFileMappingW(INVALID_HANDLE_VALUE, None, PAGE_READWRITE, 0, 8, name)
        self._view = kernel32.MapViewOfFile(self._handle, FILE_MAP_ALL_ACCESS, 0, 0, 8) if self._handle else None
        self._cell = ctypes.c_uint64.from_address(self._view) if self._view else None

    @property
    def value(self) -> int:
        return int(self._cell.value) if self._cell is not None else 0

    @value.setter
    def value(self, new: int) -> None:
        if self._cell is not None:
            self._cell.value = new

    def close(self) -> None:
        self._cell = None
        if self._view:
            kernel32.UnmapViewOfFile(self._view)
            self._view = None
        if self._handle:
            kernel32.CloseHandle(self._handle)
            self._handle = None


def acquire_single_instance(name: str) -> Optional[int]:
    """Returns a mutex handle, or None if another instance already holds it."""
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, False, name)
    if not handle:
        return None
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def release_handle(handle: Optional[int]) -> None:
    if handle:
        kernel32.CloseHandle(handle)


def set_below_normal_priority() -> None:
    kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), BELOW_NORMAL_PRIORITY_CLASS)
