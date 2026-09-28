"""The What's new section the screensaver shows beside the primary maze after an update:
its countdown, when it closes, and (split_monitor) where it goes. Pure logic;
whats_new_view draws it."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

SHOW_SECONDS = 60
FADE_SECONDS = 1.5
CLOSES_IN = "Closes in "
CLOSES_AFTER = "Closes after this maze"

Measure = Callable[[str], int]


def countdown(elapsed: float) -> Optional[int]:
    """Whole seconds left, 60 down to 1, or None once the minute is over."""
    if elapsed >= SHOW_SECONDS:
        return None
    return SHOW_SECONDS - int(max(0.0, elapsed))


def footer_text(seconds: Optional[int]) -> tuple[str, str]:
    """(words, number) for the footer; the number is "" after the minute."""
    return (CLOSES_AFTER, "") if seconds is None else (CLOSES_IN, str(seconds))


def number_slot(measure: Measure) -> int:
    """Width of the widest two-digit number. The countdown is right-aligned in it, so the
    footer does not move when the count drops to one digit."""
    return max(measure(str(n)) for n in range(10, 100))


@dataclass(frozen=True)
class Footer:
    words: str
    number: str
    number_right: int  # x of the number's right edge, from the footer's left
    width: int


def footer_layout(seconds: Optional[int], measure: Measure) -> Footer:
    words, number = footer_text(seconds)
    if not number:
        width = measure(words)
        return Footer(words, "", width, width)
    right = measure(words) + number_slot(measure)
    return Footer(words, number, right, right)


class SectionClock:
    """The minute counts from when the section first appeared (a monitor change that
    rebuilds the windows keeps the same clock). The first solve that ends after the minute
    starts a FADE_SECONDS fade."""

    def __init__(self, started: float):
        self.started = started
        self.closed_at: Optional[float] = None

    def seconds_left(self, now: float) -> Optional[int]:
        return countdown(now - self.started)

    def board_solved(self, now: float) -> None:
        """The primary board finished a maze (entered its hold phase)."""
        if self.closed_at is None and now - self.started >= SHOW_SECONDS:
            self.closed_at = now

    def alpha(self, now: float) -> int:
        """255 while open, then down to 0 over FADE_SECONDS."""
        if self.closed_at is None:
            return 255
        left = 1.0 - (now - self.closed_at) / FADE_SECONDS
        return max(0, min(255, round(255 * left)))

    def faded(self, now: float) -> bool:
        return self.closed_at is not None and now - self.closed_at >= FADE_SECONDS
