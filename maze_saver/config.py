"""Settings: defaults, validation, and the JSON file on disk."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Optional, Union

FpsCap = Union[str, int]


@dataclass(frozen=True)
class Settings:
    min_cells: int = 12
    max_cells: int = 40
    gen_speed: float = 60.0
    solve_speed: float = 20.0
    lookahead: int = 4
    hold_seconds: float = 4.0
    max_leads: int = 12
    fps_cap: FpsCap = "auto"
    check_updates: bool = True


# name -> (low, high, is_int); both bounds inclusive.
NUMERIC_RANGES = {
    "min_cells": (4, 200, True),
    "max_cells": (4, 200, True),
    "gen_speed": (5, 1000, False),
    "solve_speed": (2, 500, False),
    "lookahead": (0, 12, True),
    "hold_seconds": (0, 30, False),
    "max_leads": (2, 16, True),
}
FPS_CAP_CHOICES = ("auto", 60, 120)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _numeric(value: Any, low: float, high: float, is_int: bool) -> Optional[float]:
    if not _is_number(value):
        return None
    if is_int:
        if not float(value).is_integer():
            return None
        value = int(value)
    else:
        value = float(value)
    return value if low <= value <= high else None


def _fps_cap(value: Any) -> Optional[FpsCap]:
    if value == "auto":
        return "auto"
    if _is_number(value) and value in (60, 120):
        return int(value)
    return None


def from_dict(raw: Any) -> Settings:
    """Build Settings from untrusted data. Bad or missing keys keep their defaults."""
    if not isinstance(raw, dict):
        return Settings()
    values: dict[str, Any] = {}
    for name, (low, high, is_int) in NUMERIC_RANGES.items():
        if name in raw:
            value = _numeric(raw[name], low, high, is_int)
            if value is not None:
                values[name] = value
    if "fps_cap" in raw:
        cap = _fps_cap(raw["fps_cap"])
        if cap is not None:
            values["fps_cap"] = cap
    if isinstance(raw.get("check_updates"), bool):
        values["check_updates"] = raw["check_updates"]
    settings = replace(Settings(), **values)
    if settings.min_cells > settings.max_cells:
        settings = replace(settings, min_cells=settings.max_cells, max_cells=settings.min_cells)
    return settings


def app_data() -> Path:
    """The per-user settings folder: %APPDATA% on Windows, $XDG_CONFIG_HOME (~/.config) elsewhere."""
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA") or str(Path.home()))
    return Path(os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config"))


def default_path() -> Path:
    return app_data() / "Labyrinth Screensaver" / "config.json"


def legacy_path() -> Path:
    """Where settings lived before the project was renamed Labyrinth."""
    return app_data() / "MazeScreensaver" / "config.json"


def adopt_legacy(target: Path, legacy: Path) -> None:
    """Copy settings from their pre-rename location once, if the new file is missing.
    Never raises: a failed copy just means starting from defaults."""
    try:
        if not target.exists() and legacy.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(legacy.read_bytes())
    except OSError:
        pass


def load(path: Optional[Path] = None) -> Settings:
    """Read settings. Never raises: any problem gives defaults."""
    if path is None:
        path = default_path()
        adopt_legacy(path, legacy_path())
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Settings()
    return from_dict(raw)


def save(settings: Settings, path: Optional[Path] = None) -> None:
    target = Path(path or default_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
