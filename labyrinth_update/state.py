"""What the updater remembers between runs: when it last checked, what it found, and which
version the user dismissed. Stored as update.json next to each product's settings."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .notes import MAX_ENTRIES, NoteEntry
from .releases import Release, is_sha256
from .version import parse_version

CHECK_INTERVAL = 7 * 24 * 3600  # seconds
STALE_TEMP_AGE = 3600  # seconds; a save's temp file older than this was left by a killed run


@dataclass(frozen=True)
class UpdateState:
    last_check: Optional[float] = None  # time.time() of the last successful check
    found: Optional[Release] = None  # newest release that check saw, if any
    dismissed: Optional[str] = None  # version the user chose to hide
    notes: tuple[NoteEntry, ...] = ()  # release notes, newest first (notes.merge_notes)
    # The version whose What's new was last seen, or the first version that ran with this
    # feature. Lower than the running version means What's new is still to be shown.
    last_run_version: Optional[str] = None
    whats_new_runs: int = 0  # screensaver runs that showed What's new without finishing it


def _notes(raw: Any) -> tuple[NoteEntry, ...]:
    if not isinstance(raw, list):
        return ()
    entries = []
    for item in raw[:MAX_ENTRIES]:
        if (isinstance(item, dict) and parse_version(item.get("version")) is not None
                and isinstance(item.get("notes"), str)):
            entries.append(NoteEntry(item["version"], item["notes"]))
    return tuple(entries)


def _release(raw: Any) -> Optional[Release]:
    if not isinstance(raw, dict):
        return None
    version, url, sha = raw.get("version"), raw.get("url"), raw.get("sha256")
    if parse_version(version) is None or not isinstance(url, str) or not is_sha256(sha):
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
    last_run = raw.get("last_run_version")
    if parse_version(last_run) is None:
        last_run = None
    runs = raw.get("whats_new_runs")
    if not isinstance(runs, int) or isinstance(runs, bool) or runs < 0:
        runs = 0
    return UpdateState(None if last is None else float(last), _release(raw.get("found")),
                       dismissed, _notes(raw.get("notes")), last_run, runs)


def remove_stale_temps(target: Path, now: Optional[float] = None) -> None:
    """Delete target's temp files (name.<pid>.tmp) older than STALE_TEMP_AGE, which a run
    killed mid-save leaves behind. Newer ones may belong to a save in progress. Never raises."""
    now = time.time() if now is None else now
    try:
        leftovers = list(target.parent.glob(f"{target.name}.*.tmp"))
    except OSError:
        return
    for tmp in leftovers:
        try:
            if now - tmp.stat().st_mtime > STALE_TEMP_AGE:
                tmp.unlink()
        except OSError:
            pass


def save(path: Path, state: UpdateState) -> None:
    """Raises OSError if the file cannot be written."""
    found = None
    if state.found is not None:
        found = {"version": state.found.version, "url": state.found.url,
                 "sha256": state.found.sha256}
    data = {"last_check": state.last_check, "found": found, "dismissed": state.dismissed,
            "notes": [{"version": e.version, "notes": e.notes} for e in state.notes],
            "last_run_version": state.last_run_version,
            "whats_new_runs": state.whats_new_runs}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    remove_stale_temps(target)
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


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
