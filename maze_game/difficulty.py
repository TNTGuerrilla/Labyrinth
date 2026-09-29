"""Difficulty presets and how big a maze is for a given play area.

Difficulty sets the number of cells on the maze's short side. The long side then
fills the play area's aspect ratio, the way the screensaver fills a monitor.
"""
from __future__ import annotations

import random

PRESETS = {"small": (8, 12), "medium": (13, 24), "large": (25, 48), "xl": (49, 96)}
DIFFICULTIES = ("small", "medium", "large", "xl", "custom")
LABELS = {"small": "Small", "medium": "Medium", "large": "Large", "xl": "XL", "custom": "Custom"}
MIN_CUSTOM = 4


def _fill(px: int, coverage: int = 100) -> int:
    """`coverage` percent of a pixel length, rounded down."""
    return px * coverage // 100


def ceiling(view_w: int, view_h: int, coverage: int = 100) -> int:
    """Largest short side that still gives every cell at least 1 px at 100% zoom."""
    return max(MIN_CUSTOM, _fill(min(view_w, view_h), coverage))


def size_range(difficulty: str, custom_min: int, custom_max: int, cap: int) -> tuple[int, int]:
    if difficulty == "custom":
        lo, hi = sorted((custom_min, custom_max))
    else:
        lo, hi = PRESETS[difficulty]
    lo = max(MIN_CUSTOM, min(lo, cap))
    hi = max(lo, min(hi, cap))
    return lo, hi


def pick_short(difficulty: str, custom_min: int, custom_max: int, view_w: int, view_h: int,
               rng: random.Random, coverage: int = 100) -> int:
    lo, hi = size_range(difficulty, custom_min, custom_max, ceiling(view_w, view_h, coverage))
    return rng.randint(lo, hi)


def grid_size(short: int, view_w: int, view_h: int, coverage: int = 100) -> tuple[int, int]:
    """(cols, rows) for a maze with `short` cells on its short side in this play area."""
    short_fill = max(1, _fill(min(view_w, view_h), coverage))
    long_fill = _fill(max(view_w, view_h), coverage)
    long = max(short, long_fill * short // short_fill)
    return (long, short) if view_w >= view_h else (short, long)
