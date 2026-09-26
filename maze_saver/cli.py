"""Parse the flags Windows passes to a screensaver (/s, /c[:hwnd], /p hwnd)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Command:
    mode: str  # "saver", "config", "preview", "window" or "none"
    hwnd: Optional[int] = None
    multiwindow: bool = False
    leads: Optional[int] = None


def _parse_int(text: str) -> Optional[int]:
    try:
        return int(text.strip())
    except ValueError:
        return None


def _parse_leads(text: str) -> Optional[int]:
    value = _parse_int(text)
    if value is None or not 1 <= value <= 16:
        return None
    return value


def parse_args(argv: Sequence[str]) -> Command:
    args = list(argv)
    multiwindow = "--multiwindow" in args
    args = [a for a in args if a != "--multiwindow"]
    leads = None
    if "--leads" in args:
        i = args.index("--leads")
        if i + 1 < len(args):
            leads = _parse_leads(args[i + 1])
            del args[i:i + 2]
        else:
            del args[i]
    if "--window" in args:
        return Command("window", leads=leads)
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
        return Command("saver", multiwindow=multiwindow, leads=leads)
    if letter == "p":
        return Command("preview", hwnd) if hwnd is not None else Command("none")
    return Command("config", hwnd)
