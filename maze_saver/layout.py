"""Pure monitor-layout math: which window(s) to open and where each board goes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Union

MAX_WINDOW_SIDE = 16384
MAX_WASTE_RATIO = 3.0
FPS_MIN, FPS_MAX = 30, 240
DEFAULT_HZ = 60


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return self.w * self.h

    def moved(self, dx: int, dy: int) -> Rect:
        return Rect(self.x + dx, self.y + dy, self.w, self.h)

    def contains(self, other: Rect) -> bool:
        return (self.x <= other.x and self.y <= other.y
                and other.right <= self.right and other.bottom <= self.bottom)


@dataclass(frozen=True)
class Monitor:
    x: int
    y: int
    w: int
    h: int
    dpi: int = 96
    hz: int = DEFAULT_HZ
    name: str = ""

    @property
    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.w, self.h)


@dataclass(frozen=True)
class Layout:
    multiwindow: bool
    window: Rect  # bounding box of all monitors, desktop coordinates
    boards: tuple[Rect, ...]  # one per monitor, desktop coordinates
    fps: int


def bounding_box(monitors: Sequence[Monitor]) -> Rect:
    left = min(m.x for m in monitors)
    top = min(m.y for m in monitors)
    right = max(m.x + m.w for m in monitors)
    bottom = max(m.y + m.h for m in monitors)
    return Rect(left, top, right - left, bottom - top)


def needs_multiwindow(monitors: Sequence[Monitor]) -> bool:
    box = bounding_box(monitors)
    if box.w > MAX_WINDOW_SIDE or box.h > MAX_WINDOW_SIDE:
        return True
    return box.area > MAX_WASTE_RATIO * sum(m.w * m.h for m in monitors)


def frame_cap(monitors: Sequence[Monitor], setting: Union[str, int]) -> int:
    if setting != "auto":
        return int(setting)
    rates = [m.hz if m.hz > 1 else DEFAULT_HZ for m in monitors] or [DEFAULT_HZ]
    return max(FPS_MIN, min(FPS_MAX, max(rates)))


def plan_layout(monitors: Sequence[Monitor], fps_setting: Union[str, int],
                force_multiwindow: bool = False) -> Layout:
    if not monitors:
        raise ValueError("no monitors to lay out")
    return Layout(
        multiwindow=force_multiwindow or needs_multiwindow(monitors),
        window=bounding_box(monitors),
        boards=tuple(m.rect for m in monitors),
        fps=frame_cap(monitors, fps_setting),
    )


def scale_to_fit(monitors: Sequence[Monitor], max_w: int,
                 max_h: int) -> tuple[tuple[int, int], list[Rect]]:
    """Shrink the whole layout to fit max_w x max_h (never enlarge). Rects are window-local."""
    box = bounding_box(monitors)
    scale = min(max_w / box.w, max_h / box.h, 1.0)
    size = (max(1, int(box.w * scale)), max(1, int(box.h * scale)))
    rects = []
    for m in monitors:
        x = int((m.x - box.x) * scale)
        y = int((m.y - box.y) * scale)
        right = int((m.x + m.w - box.x) * scale)
        bottom = int((m.y + m.h - box.y) * scale)
        rects.append(Rect(x, y, max(1, right - x), max(1, bottom - y)))
    return size, rects
