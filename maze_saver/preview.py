"""Pure rules for the Screen Saver Settings preview: when to keep drawing, and which
Labyrinth preview owns a given preview window when Windows starts several for it."""
from __future__ import annotations

CLAIM_PREFIX = "Local\\LabyrinthScreensaverPreview-"
_MASK32 = 0xFFFFFFFF


def preview_should_run(parent_alive: bool, child_alive: bool, superseded: bool) -> bool:
    """Draw only while Windows' preview window and our child inside it both exist and no
    newer Labyrinth preview has claimed the same preview window."""
    return parent_alive and child_alive and not superseded


def claim_name(parent_hwnd: int) -> str:
    """Name of the shared slot that records the newest preview for this preview window."""
    return f"{CLAIM_PREFIX}{int(parent_hwnd)}"


def make_token(pid: int, serial: int) -> int:
    """A nonzero 64-bit id for one preview: process id in the high half, a per-process
    serial (starting at 1) in the low half."""
    return ((pid & _MASK32) << 32) | (serial & _MASK32) or 1


def is_superseded(mine: int, current: int) -> bool:
    """True when the slot holds another preview's token. An empty (zero) slot never
    supersedes, so a slot that was never written cannot end a preview."""
    return current != 0 and current != mine
