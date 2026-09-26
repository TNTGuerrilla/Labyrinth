"""Decides when user input should end the screensaver. Pure logic."""
from __future__ import annotations

GRACE_SECONDS = 0.5
MOVE_THRESHOLD_PX = 8


class ExitWatcher:
    def __init__(self, start_time: float, cursor: tuple[int, int],
                 grace: float = GRACE_SECONDS, threshold: int = MOVE_THRESHOLD_PX):
        self._start = start_time
        self._origin = cursor
        self._grace = grace
        self._threshold_sq = threshold * threshold

    def should_exit(self, now: float, cursor: tuple[int, int], input_event: bool) -> bool:
        if now - self._start < self._grace:
            # Windows can send spurious input at launch; keep re-anchoring the cursor.
            self._origin = cursor
            return False
        if input_event:
            return True
        dx = cursor[0] - self._origin[0]
        dy = cursor[1] - self._origin[1]
        return dx * dx + dy * dy > self._threshold_sq
