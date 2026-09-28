"""Which version of a product is running, and where the running program is on disk."""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

_VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")
_HERE = Path(__file__).resolve().parent
# Taken at import, before anything can change the working directory.
_RAW_ARGV0 = sys.argv[0] if sys.argv and sys.argv[0] else None
_ARGV0 = os.path.abspath(_RAW_ARGV0) if _RAW_ARGV0 else None


def parse_version(text: object) -> Optional[tuple[int, int, int]]:
    """(major, minor, patch) for "X.Y.Z", or None for anything else."""
    if not isinstance(text, str):
        return None
    match = _VERSION.fullmatch(text.strip())
    if match is None:
        return None
    major, minor, patch = (int(g) for g in match.groups())
    return major, minor, patch


def is_built() -> bool:
    """True in a Nuitka build: Nuitka defines __compiled__ in every compiled module."""
    return "__compiled__" in globals()


def versions_file() -> Path:
    """versions.json: bundled next to this module in builds, at the repo root from source."""
    bundled = _HERE / "versions.json"
    return bundled if bundled.is_file() else _HERE.parent / "versions.json"


def running_version(key: str, path: Optional[Path] = None) -> Optional[str]:
    """The version for `key` ("game" or "screensaver") in versions.json, or None."""
    try:
        data = json.loads((path or versions_file()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = data.get(key) if isinstance(data, dict) else None
    return value if parse_version(value) is not None else None


def current_binary(argv0: Optional[str] = None, built: Optional[bool] = None) -> Optional[Path]:
    """The program file the user started (the onefile .exe, .scr or Linux binary). resolve()
    expands Windows short 8.3 names, which Windows may use when it starts a screensaver.
    A bare name (`labyrinth` typed in a Linux shell) is looked up on PATH. None when running
    from source or when the file cannot be found."""
    if not (is_built() if built is None else built):
        return None
    raw, start = (_RAW_ARGV0, _ARGV0) if argv0 is None else (argv0, argv0)
    if not raw or not start:
        return None
    path = Path(start).resolve()
    if path.is_file():
        return path
    if "/" in raw or os.sep in raw:
        return None
    found = shutil.which(raw)
    if found is None:
        return None
    path = Path(found).resolve()
    return path if path.is_file() else None
