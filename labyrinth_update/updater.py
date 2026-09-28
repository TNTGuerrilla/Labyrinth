"""The update state machine the game and the screensaver share. Network and disk work runs
on a background thread; the UI reads `snapshot` each frame or timer tick."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Optional

from . import state as state_file
from . import whats_new as news
from .install import cleanup_old
from .net import Progress, UpdateError
from .notes import collect_notes, merge_notes
from .releases import Product, Release, fetch_releases, newest
from .version import current_binary, running_version
from .whats_new import WhatsNew

IDLE, AVAILABLE, DOWNLOADING, READY, FAILED = "idle", "available", "downloading", "ready", "failed"
NOT_CHECKED, CHECKING, UP_TO_DATE, CHECK_FAILED = (
    "not_checked", "checking", "up_to_date", "check_failed")
DEBUG_ENV = "LABYRINTH_UPDATE_DEBUG"  # a file path: builds write what the updater sees there

Installer = Callable[[Release, Progress], None]


@dataclass(frozen=True)
class Snapshot:
    status: str = IDLE
    release: Optional[Release] = None
    progress: float = 0.0  # 0 to 1 while DOWNLOADING
    message: str = ""  # why it FAILED


@dataclass(frozen=True)
class CheckReport:
    """The outcome of the latest check, for the Info section's status line."""
    status: str = NOT_CHECKED
    message: str = ""  # why a Check now failed


class Updater:
    def __init__(self, product: Product, current: str, state_path: Path, enabled: bool,
                 fetch: Callable[[], Any] = fetch_releases,
                 clock: Callable[[], float] = time.time, target: Optional[Path] = None):
        self.product = product
        self.current = current
        self.state_path = state_path
        self.enabled = enabled
        self.target = target
        self._fetch = fetch
        self._clock = clock
        self._lock = threading.RLock()
        self._check_thread: Optional[threading.Thread] = None
        self._install_thread: Optional[threading.Thread] = None
        self._state = state_file.load(state_path)
        self._asked = False  # Check now ran this session: offer even with weekly checks off
        self._asking = False  # a Check now waits for the check in flight to report
        self._report = CheckReport()
        self._snapshot = self._offer()

    @property
    def snapshot(self) -> Snapshot:
        with self._lock:
            return self._snapshot

    def _set(self, snapshot: Snapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    @property
    def check_report(self) -> CheckReport:
        with self._lock:
            return self._report

    def _offer(self) -> Snapshot:
        allowed = self.enabled or self._asked
        release = state_file.visible(self._state, self.current) if allowed else None
        return Snapshot(AVAILABLE, release) if release is not None else Snapshot()

    def _start_check(self) -> None:
        self._report = CheckReport(CHECKING)
        self._check_thread = threading.Thread(target=self._check, daemon=True)
        self._check_thread.start()

    def _check_busy(self) -> bool:
        return self._check_thread is not None and self._check_thread.is_alive()

    def _install_busy(self) -> bool:
        return self._install_thread is not None and self._install_thread.is_alive()

    def _save(self) -> None:
        try:
            state_file.save(self.state_path, self._state)
        except OSError:
            pass

    def check(self, force: bool = False) -> None:
        """Ask GitHub in the background when enabled and a week has passed, or when forced
        (a settings screen was opened). A running install is left alone; a click on Update
        must not be dropped just because a check is also in flight."""
        with self._lock:
            if not self.enabled or self._check_busy() or self._install_busy():
                return
            if not force and not state_file.is_due(self._state, self._clock()):
                return
            self._start_check()

    def check_now(self) -> None:
        """The user pressed Check now: check even with weekly checks off, report the outcome
        (Up to date, or why it failed), and offer a dismissed version again."""
        with self._lock:
            if self._install_busy():
                return
            self._asking = True
            self._report = CheckReport(CHECKING)
            if self._check_busy():
                return  # the check in flight reports to this request when it ends
            self._start_check()

    def _check_failed(self, message: str) -> None:
        with self._lock:
            asked, self._asking = self._asking, False
            # Automatic checks fail silently; only the user's own request hears about it.
            self._report = CheckReport(CHECK_FAILED, message) if asked else CheckReport()

    def _check(self) -> None:
        try:
            listing = self._fetch()
            found = newest(listing, self.product, self.current)
            fresh = ([] if found is None
                     else collect_notes(listing, self.product, self.current, found.version))
        except UpdateError as exc:
            self._check_failed(str(exc))  # offline or rate limited: try again next launch
            return
        except Exception:
            self._check_failed("Could not check for updates.")  # a bug reading the list
            return
        with self._lock:
            asked, self._asking = self._asking, False
            state = replace(self._state, last_check=self._clock(), found=found)
            if found is not None:  # the spec stores notes only when something newer exists
                state = replace(state, notes=merge_notes(state.notes, fresh, self.current))
                if asked and found.version == state.dismissed:
                    state = replace(state, dismissed=None)  # the user asked: offer it again
            self._state = state
            self._save()
            self._report = CheckReport(UP_TO_DATE) if found is None else CheckReport()
            if asked:
                self._asked = True
            if not (self.enabled or self._asked):
                return  # turned off while the check was in flight: never re-show
            current = self._snapshot
            if current.status in (IDLE, AVAILABLE):
                self._snapshot = self._offer()
            elif current.status == FAILED:
                # An install may have failed on an older release while this check was
                # already running: show the newly found one instead of the stale failure.
                visible = state_file.visible(self._state, self.current)
                if visible is not None and (current.release is None
                                             or visible.version != current.release.version):
                    self._snapshot = Snapshot(AVAILABLE, visible)
            # DOWNLOADING and READY are never overwritten by a finishing check.

    def set_enabled(self, enabled: bool) -> None:
        with self._lock:
            self.enabled = enabled
            if self._snapshot.status in (IDLE, AVAILABLE):
                self._snapshot = self._offer()
        if enabled:
            self.check()

    def dismiss(self) -> None:
        """Hide the offered version until a newer one appears."""
        with self._lock:
            snap = self._snapshot
            if snap.release is None or snap.status not in (AVAILABLE, FAILED):
                return
            self._state = replace(self._state, dismissed=snap.release.version)
            self._save()
            self._snapshot = Snapshot()

    def install(self, installer: Installer) -> None:
        """Run installer(release, progress) in the background for the offered release. A
        check that is also running does not block this; only another install does."""
        with self._lock:
            if self._install_busy():
                return
            snap = self._snapshot
            if snap.release is None or snap.status not in (AVAILABLE, FAILED):
                return
            release = snap.release
            self._snapshot = Snapshot(DOWNLOADING, release)

            def progress(fraction: float) -> None:
                self._set(Snapshot(DOWNLOADING, release, fraction))

            def work() -> None:
                try:
                    installer(release, progress)
                except UpdateError as exc:
                    self._set(Snapshot(FAILED, release, message=str(exc)))
                    return
                except OSError as exc:
                    self._set(Snapshot(FAILED, release,
                                       message=f"The update could not be installed: {exc}"))
                    return
                except Exception:
                    self._set(Snapshot(FAILED, release,
                                       message="The update could not be installed."))
                    return
                self._set(Snapshot(READY, release))

            self._install_thread = threading.Thread(target=work, daemon=True)
            self._install_thread.start()

    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for background work to finish."""
        if self._check_thread is not None:
            self._check_thread.join(timeout)
        if self._install_thread is not None:
            self._install_thread.join(timeout)

    def _apply(self, state: state_file.UpdateState) -> None:
        if state != self._state:
            self._state = state
            self._save()

    def start_whats_new(self) -> Optional[WhatsNew]:
        """Call once when the program starts: the What's new to show now, or None. A first
        run records the running version. Order against a check does not matter: a check
        keeps every stored note at or below the running version (notes.merge_notes)."""
        with self._lock:
            state, shown = news.on_start(self._state, self.current)
            self._apply(state)
            return shown

    def count_whats_new_run(self) -> None:
        with self._lock:
            self._apply(news.count_run(self._state, self.current))

    def mark_whats_new_seen(self) -> None:
        with self._lock:
            self._apply(news.mark_seen(self._state, self.current))

    def running_whats_new(self) -> WhatsNew:
        with self._lock:
            return news.running_notes(self._state, self.current)


def _debug_dump(target: Optional[Path], current: Optional[str]) -> None:
    path = os.environ.get(DEBUG_ENV)
    if not path:
        return
    data = {"binary": None if target is None else str(target), "version": current,
            "argv": sys.argv}
    try:
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def for_program(product: Product, settings_dir: Path, enabled: bool) -> Optional[Updater]:
    """An Updater for the running build, or None when running from source or when the
    version is unknown. Also deletes copies left behind by the previous update."""
    target = current_binary()
    current = running_version(product.key)
    _debug_dump(target, current)
    if target is None or current is None:
        return None
    cleanup_old(target)
    return Updater(product, current, settings_dir / "update.json", enabled, target=target)
