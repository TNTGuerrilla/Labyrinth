"""Parse the flags Windows passes to a screensaver (/s, /c[:hwnd], /p hwnd)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Command:
    mode: str  # "saver", "config", "preview", "window" or "none"
    hwnd: Optional[int] = None
    multiwindow: bool = False


def _parse_int(text: str) -> Optional[int]:
    try:
        return int(text.strip())
    except ValueError:
        return None


def parse_args(argv: Sequence[str]) -> Command:
    args = list(argv)
    multiwindow = "--multiwindow" in args
    args = [a for a in args if a != "--multiwindow"]
    if "--window" in args:
        return Command("window")
    if not args:
        return Command("config")
    first = args[0].strip()
    if len(first) < 2 or first[0] not in "/-":
        return Command("config")
    letter = first[1].lower()
    rest = first[2:].lstrip(":")
    if rest:
        hwnd = _parse_int(rest)
    else:
        hwnd = _parse_int(args[1]) if len(args) > 1 else None
    if letter == "s":
        return Command("saver", multiwindow=multiwindow)
    if letter == "p":
        return Command("preview", hwnd) if hwnd is not None else Command("none")
    return Command("config", hwnd)
