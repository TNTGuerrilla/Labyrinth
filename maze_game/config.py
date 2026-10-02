"""Game settings and key bindings: defaults, validation, and the JSON file on disk."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Optional

from maze_saver.config import adopt_legacy, app_data
from maze_saver.solver import DEFAULT_SOLVER, SOLVERS

from .difficulty import DIFFICULTIES, MIN_CUSTOM
from .keymap import Keymap

MAX_CUSTOM = 100_000


@dataclass(frozen=True)
class GameSettings:
    follow_bends: bool = True  # Steering: Bend assist (wins over run_straight)
    run_straight: bool = False  # Steering: Run straight (with follow_bends off)
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
    bench_coverage: int = 100  # the coverage the benchmark ran at
    check_updates: bool = True
    grid_strength: int = 20  # percent brightness of the grid lines
    coverage: int = 100  # percent of the screen the maze fills at 100% zoom
    screensaver_solver: str = DEFAULT_SOLVER  # screensaver mode: a SOLVERS key
    screensaver_speed: float = 20.0  # screensaver mode: solver steps per second
    screensaver_lookahead: int = 4  # screensaver mode: used by Human-like and Depth-first
    screensaver_pause: float = 4.0  # screensaver mode: seconds on the solved maze


# name -> (low, high, is_int); both bounds inclusive.
NUMERIC_RANGES = {
    "glide_speed": (2, 40, False),
    "turn_pause": (0, 1, False),
    "solve_speed": (2, 500, False),
    "lookahead": (0, 12, True),
    "gen_speed": (5, 1000, False),
    "max_leads": (2, 16, True),
    "hint_length": (2, 40, True),
    "grid_strength": (10, 100, True),
    "coverage": (50, 100, True),
    "screensaver_speed": (2, 500, False),
    "screensaver_lookahead": (0, 12, True),
    "screensaver_pause": (0, 30, False),
    "custom_min": (MIN_CUSTOM, MAX_CUSTOM, True),
    "custom_max": (MIN_CUSTOM, MAX_CUSTOM, True),
}
BOOL_FIELDS = ("follow_bends", "run_straight", "animated", "multicolor", "show_grid",
               "check_updates")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _whole(value: Any) -> bool:
    """A number with no fraction. An int is never converted to float, since a huge one
    (hundreds of digits) would overflow."""
    return _is_number(value) and (isinstance(value, int) or value.is_integer())


def _numeric(value: Any, low: float, high: float, is_int: bool) -> Optional[float]:
    # The range check comes first: comparing a huge int is exact, converting it is not.
    if (not _is_number(value) or (is_int and not _whole(value))
            or not low <= value <= high):
        return None
    return int(value) if is_int else float(value)


def _bench(raw: dict) -> dict:
    """The benchmark fields, only when all of them are valid together. A result saved
    without its coverage counts as 100%: the default, and the only coverage before the
    setting existed."""
    size = _numeric(raw.get("bench_size"), MIN_CUSTOM, MAX_CUSTOM, True)
    rate = raw.get("bench_rate")
    res = raw.get("bench_resolution")
    low, high, _ = NUMERIC_RANGES["coverage"]
    coverage = _numeric(raw.get("bench_coverage", 100), low, high, True)
    if size is None or coverage is None or not _is_number(rate) or not 0 < rate < 1:
        return {}
    if (not isinstance(res, (list, tuple)) or len(res) != 2
            or not all(_whole(v) and v >= 1 for v in res)):
        return {}
    return {"bench_size": size, "bench_rate": float(rate),
            "bench_resolution": (int(res[0]), int(res[1])), "bench_coverage": coverage}


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
    if isinstance(raw.get("screensaver_solver"), str) and raw["screensaver_solver"] in SOLVERS:
        values["screensaver_solver"] = raw["screensaver_solver"]
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
    except (OSError, ValueError, RecursionError):  # RecursionError: deeply nested JSON
        return GameSettings(), Keymap()
    if not isinstance(raw, dict):
        return GameSettings(), Keymap()
    return from_dict(raw.get("settings")), Keymap.from_json(raw.get("keys"), valid_key)


def save(settings: GameSettings, keymap: Keymap, path: Optional[Path] = None) -> None:
    """Write a temp file beside the target and swap it in, so a crash mid-write cannot
    leave a half-written config.json. Raises OSError if the file cannot be written."""
    target = Path(path or default_path())
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {"settings": asdict(settings), "keys": keymap.to_json()}
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
