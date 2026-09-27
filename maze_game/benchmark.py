"""Benchmark math: frame-rate score, the size search and build-time estimates.

The scene that produces frame times lives in app.py; everything here is pure.
"""
from __future__ import annotations

import statistics
from typing import Callable, Iterable, Optional, Sequence

TARGET_FPS = 60.0
START_SIZE = 96
TOLERANCE = 4
MIN_SIZE = 4
DROP_SLOWEST = 0.10
BUILD_FRACTION = 0.8  # the scene builds this much of the maze synchronously, timed
FINISH_SECONDS = 3.0  # cap on the rendered fast-forward of the remaining growth
RUN_SECONDS = 2.0  # cap on the rendered perfect run


def score(frame_times: Sequence[float]) -> float:
    """Average fps after discarding the slowest 10% of frames."""
    times = sorted(t for t in frame_times if t > 0)
    if not times:
        return 0.0
    keep = times[:max(1, len(times) - int(len(times) * DROP_SLOWEST))]
    return sum(1.0 / t for t in keep) / len(keep)


def find_recommended(measure: Callable[[int], float], ceiling: int,
                     on_step: Optional[Callable[[int], None]] = None) -> int:
    """Largest short side (within TOLERANCE) whose measured fps is at least TARGET_FPS.
    Starts at START_SIZE, doubles while passing (or halves while failing), then bisects
    between the last passing and first failing size."""
    ceiling = max(MIN_SIZE, ceiling)

    def passes(n: int) -> bool:
        if on_step is not None:
            on_step(n)
        return measure(n) >= TARGET_FPS

    n = min(START_SIZE, ceiling)
    if passes(n):
        lo = n
        while True:
            if lo >= ceiling:
                return ceiling
            n = min(lo * 2, ceiling)
            if not passes(n):
                hi = n
                break
            lo = n
    else:
        hi = n
        while True:
            if hi <= MIN_SIZE:
                return MIN_SIZE
            n = max(MIN_SIZE, (hi + 1) // 2)
            if passes(n):
                lo = n
                break
            hi = n
    while hi - lo > TOLERANCE:
        mid = (lo + hi) // 2
        if passes(mid):
            lo = mid
        else:
            hi = mid
    return lo


def median(values: Iterable[float]) -> float:
    return float(statistics.median(values))


def build_seconds(cells: int, rate: float) -> float:
    return cells * rate


def build_text(seconds: float) -> str:
    if seconds < 0.1:
        return "Building is instant"
    if seconds < 10:
        return f"Building takes about {seconds:.1f} s"
    return f"Building takes about {seconds:.0f} s"
