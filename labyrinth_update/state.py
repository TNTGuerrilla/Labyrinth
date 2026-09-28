"""What the updater remembers between runs: when it last checked, what it found, and which
version the user dismissed. Stored as update.json next to each product's settings."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .releases import Release
from .version import parse_version

CHECK_INTERVAL = 7 * 24 * 3600  # seconds


@dataclass(frozen=True)
class UpdateState:
    last_check: Optional[float] = None  # time.time() of the last successful check
    found: Optional[Release] = None  # newest release that check saw, if any
    dismissed: Optional[str] = None  # version the user chose to hide


def _release(raw: Any) -> Optional[Release]:
    if not isinstance(raw, dict):
        return None
    version, url, sha = raw.get("version"), raw.get("url"), raw.get("sha256")
    if parse_version(version) is None or not isinstance(url, str) or not isinstance(sha, str):
        return None
    return Release(version, url, sha)


def load(path: Path) -> UpdateState:
    """Never raises: a missing or damaged file means a fresh state."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return UpdateState()
    if not isinstance(raw, dict):
        return UpdateState()
    last = raw.get("last_check")
    if not isinstance(last, (int, float)) or isinstance(last, bool):
        last = None
    dismissed = raw.get("dismissed")
    if parse_version(dismissed) is None:
        dismissed = None
    return UpdateState(None if last is None else float(last), _release(raw.get("found")),
                       dismissed)


def save(path: Path, state: UpdateState) -> None:
    """Raises OSError if the file cannot be written."""
    found = None
    if state.found is not None:
        found = {"version": state.found.version, "url": state.found.url,
                 "sha256": state.found.sha256}
    data = {"last_check": state.last_check, "found": found, "dismissed": state.dismissed}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_due(state: UpdateState, now: float) -> bool:
    """Due on the first run, a week after the last check, or if the clock went back."""
    if state.last_check is None:
        return True
    age = now - state.last_check
    return age < 0 or age >= CHECK_INTERVAL


def visible(state: UpdateState, current: str) -> Optional[Release]:
    """The release to offer: newer than the running version and not dismissed."""
    found = state.found
    if found is None or found.version == state.dismissed:
        return None
    ours, theirs = parse_version(current), parse_version(found.version)
    if ours is None or theirs is None or theirs <= ours:
        return None
    return found
