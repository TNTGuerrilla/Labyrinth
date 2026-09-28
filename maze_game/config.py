"""Game settings and key bindings: defaults, validation, and the JSON file on disk."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Optional

from maze_saver.config import adopt_legacy, app_data

from .difficulty import DIFFICULTIES, MIN_CUSTOM
from .keymap import Keymap

MAX_CUSTOM = 100_000


@dataclass(frozen=True)
class GameSettings:
    follow_bends: bool = True
    animated: bool = True
    multicolor: bool = True
    show_grid: bool = True
    glide_speed: float = 5.0
    turn_pause: float = 0.2
    solve_speed: float = 20.0
    lookahead: int = 4
    gen_speed: float = 60.0
    max_leads: int = 12
    hint_length: int = 8
    difficulty: str = "medium"
    custom_min: int = 20
    custom_max: int = 40
    bench_size: Optional[int] = None
    bench_rate: Optional[float] = None  # seconds to build one cell
    bench_resolution: Optional[tuple[int, int]] = None


# name -> (low, high, is_int); both bounds inclusive.
NUMERIC_RANGES = {
    "glide_speed": (2, 40, False),
    "turn_pause": (0, 1, False),
    "solve_speed": (2, 500, False),
    "lookahead": (0, 12, True),
    "gen_speed": (5, 1000, False),
    "max_leads": (2, 16, True),
    "hint_length": (2, 40, True),
    "custom_min": (MIN_CUSTOM, MAX_CUSTOM, True),
    "custom_max": (MIN_CUSTOM, MAX_CUSTOM, True),
}
BOOL_FIELDS = ("follow_bends", "animated", "multicolor", "show_grid")


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


def _bench(raw: dict) -> dict:
    """The three benchmark fields, only when all three are valid together."""
    size = _numeric(raw.get("bench_size"), MIN_CUSTOM, MAX_CUSTOM, True)
    rate = raw.get("bench_rate")
    res = raw.get("bench_resolution")
    if size is None or not _is_number(rate) or not 0 < rate < 1:
        return {}
    if (not isinstance(res, (list, tuple)) or len(res) != 2
            or not all(_is_number(v) and float(v).is_integer() and v >= 1 for v in res)):
        return {}
    return {"bench_size": size, "bench_rate": float(rate),
            "bench_resolution": (int(res[0]), int(res[1]))}


def from_dict(raw: Any) -> GameSettings:
    """Build settings from untrusted data. Bad or missing fields keep their defaults."""
    if not isinstance(raw, dict):
        return GameSettings()
    values: dict[str, Any] = {}
    for name, (low, high, is_int) in NUMERIC_RANGES.items():
        if name in raw:
            value = _numeric(raw[name], low, high, is_int)
            if value is not None:
                values[name] = value
    for name in BOOL_FIELDS:
        if isinstance(raw.get(name), bool):
            values[name] = raw[name]
    if raw.get("difficulty") in DIFFICULTIES:
        values["difficulty"] = raw["difficulty"]
    values.update(_bench(raw))
    return replace(GameSettings(), **values)


def default_path() -> Path:
    return app_data() / "Labyrinth" / "config.json"


def legacy_path() -> Path:
    """Where settings lived before the project was renamed Labyrinth."""
    return app_data() / "MazeGame" / "config.json"


def load(path: Optional[Path] = None,
         valid_key: Optional[Callable[[str], bool]] = None) -> tuple[GameSettings, Keymap]:
    """Read settings and keys. Never raises: any problem gives defaults."""
    if path is None:
        path = default_path()
        adopt_legacy(path, legacy_path())
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return GameSettings(), Keymap()
    if not isinstance(raw, dict):
        return GameSettings(), Keymap()
    return from_dict(raw.get("settings")), Keymap.from_json(raw.get("keys"), valid_key)


def save(settings: GameSettings, keymap: Keymap, path: Optional[Path] = None) -> None:
    target = Path(path or default_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {"settings": asdict(settings), "keys": keymap.to_json()}
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
