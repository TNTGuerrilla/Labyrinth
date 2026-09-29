"""The What's new section the screensaver shows beside the primary maze after an update:
its countdown, when it closes, and (card_size, split_monitor) where it goes. Pure logic;
whats_new_view draws it."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from labyrinth_update.notes import NoteLine

from .layout import Rect

SHOW_SECONDS = 60
FADE_SECONDS = 1.5
CLOSES_IN = "Closes in "
CLOSES_AFTER = "Closes after this maze"

Measure = Callable[[str], int]


@dataclass(frozen=True)
class SaverWhatsNew:
    title: str
    lines: tuple[NoteLine, ...]
    on_seen: Callable[[], None]  # called once, when the section has faded out


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


CARD_W, CARD_H = 540, 690  # the settings dialog's size on a monitor 1440 px on its short side
CARD_BASE = 1440
CARD_MAX_W = 0.25  # at most a quarter of the monitor's width
CARD_MAX_H = 0.8  # and 80% of its height


def card_size(w: int, h: int, scale: float = 1.0) -> tuple[int, int]:
    """The section's fixed-size card: CARD_W x CARD_H scaled by the monitor's shorter side
    over 1440, then shrunk, aspect ratio kept, to fit 25% of the width and 80% of the
    height. scale (1.25 on the TV) enlarges the card and its width limit alike, so the TV's
    card is 1.25 times the monitor's (about 506 x 647 on a 1080p screen) while the height
    limit stays 80%. Rounded half up, like Kotlin's Math.round."""
    s = min(w, h) / CARD_BASE * scale
    cw, ch = CARD_W * s, CARD_H * s
    max_w, max_h = w * CARD_MAX_W * scale, h * CARD_MAX_H
    k = min(1.0, max_w / cw, max_h / ch)
    return (min(int(cw * k + 0.5), int(max_w)), min(int(ch * k + 0.5), int(max_h)))


@dataclass(frozen=True)
class Split:
    board: Rect  # where the primary maze is laid out while the section shows
    section: Rect  # the card, border included


def split_monitor(w: int, h: int, scale: float = 1.0) -> Split:
    """Landscape: the card in a column on the right (card width plus a margin each side),
    vertically centred; portrait: in a band at the bottom, horizontally centred. The board
    keeps the rest, so the card never covers the maze."""
    cw, ch = card_size(w, h, scale)
    margin = min(w, h) // 40
    if w >= h:
        column = cw + 2 * margin
        return Split(Rect(0, 0, w - column, h),
                     Rect(w - column + margin, (h - ch) // 2, cw, ch))
    band = ch + 2 * margin
    return Split(Rect(0, 0, w, h - band), Rect((w - cw) // 2, h - band + margin, cw, ch))
