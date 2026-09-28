"""After an update: when What's new shows, which notes it shows, and when it counts as seen.
Pure rules over UpdateState; the Updater applies them under its lock and saves the result."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Sequence

from .notes import BLANK, HEADING, RELEASES_TEXT, TEXT, NoteEntry, NoteLine, parse_notes
from .state import UpdateState
from .version import parse_version

SHOW_RUNS = 3  # the screensaver shows What's new in at most this many runs


@dataclass(frozen=True)
class WhatsNew:
    version: str  # the running version
    entries: tuple[NoteEntry, ...] = ()  # newest first; empty means the fallback text

    def lines(self) -> list[NoteLine]:
        if not self.entries:
            return [NoteLine(TEXT, f"Updated to version {self.version}."),
                    NoteLine(TEXT, RELEASES_TEXT)]
        if len(self.entries) == 1:
            return parse_notes(self.entries[0].notes)
        out: list[NoteLine] = []
        for entry in self.entries:
            if out:
                out.append(NoteLine(BLANK))
            out.append(NoteLine(HEADING, f"Version {entry.version}"))
            out.extend(parse_notes(entry.notes))
        return out


def notes_between(notes: Sequence[NoteEntry], low: Optional[str],
                  high: str) -> tuple[NoteEntry, ...]:
    """Entries above `low` (no lower bound when it is None) and at or below `high`."""
    top = parse_version(high)
    bottom = None if low is None else parse_version(low)
    if top is None:
        return ()
    kept = []
    for entry in notes:
        version = parse_version(entry.version)
        if version is not None and version <= top and (bottom is None or version > bottom):
            kept.append(entry)
    return tuple(kept)


def pending(state: UpdateState, current: str) -> bool:
    """True from the first run of a newer version until its What's new counts as seen."""
    last, ours = parse_version(state.last_run_version), parse_version(current)
    return last is not None and ours is not None and last < ours


def on_start(state: UpdateState, current: str) -> tuple[UpdateState, Optional[WhatsNew]]:
    """The start rule. Nothing stored (a fresh install, or an update from a version without
    this feature): store the running version and show nothing. A lower stored version: show
    What's new; it is stored as seen later. Anything else: nothing."""
    if parse_version(current) is None:
        return state, None
    if parse_version(state.last_run_version) is None:
        return replace(state, last_run_version=current, whats_new_runs=0), None
    if pending(state, current):
        entries = notes_between(state.notes, state.last_run_version, current)
        return state, WhatsNew(current, entries)
    return state, None


def mark_seen(state: UpdateState, current: str) -> UpdateState:
    """The running version's What's new was seen. Notes at or below the previous version are
    dropped, so What's new later reopens only what this update brought."""
    if not pending(state, current):
        return state
    previous = parse_version(state.last_run_version)
    kept = tuple(e for e in state.notes
                 if (v := parse_version(e.version)) is not None and v > previous)
    return replace(state, last_run_version=current, whats_new_runs=0, notes=kept)


def count_run(state: UpdateState, current: str) -> UpdateState:
    """One more screensaver run shows What's new. The SHOW_RUNS-th run counts as seen at
    once, so a screensaver that is always interrupted cannot show it forever."""
    if not pending(state, current):
        return state
    runs = state.whats_new_runs + 1
    if runs >= SHOW_RUNS:
        return mark_seen(state, current)
    return replace(state, whats_new_runs=runs)


def running_notes(state: UpdateState, current: str) -> WhatsNew:
    """What the What's new button shows: the notes the last update brought."""
    low = state.last_run_version if pending(state, current) else None
    return WhatsNew(current, notes_between(state.notes, low, current))
