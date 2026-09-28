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
from .install import cleanup_old
from .net import Progress, UpdateError
from .releases import Product, Release, fetch_releases, newest
from .version import current_binary, running_version

IDLE, AVAILABLE, DOWNLOADING, READY, FAILED = "idle", "available", "downloading", "ready", "failed"
DEBUG_ENV = "LABYRINTH_UPDATE_DEBUG"  # a file path: builds write what the updater sees there

Installer = Callable[[Release, Progress], None]


@dataclass(frozen=True)
class Snapshot:
    status: str = IDLE
    release: Optional[Release] = None
    progress: float = 0.0  # 0 to 1 while DOWNLOADING
    message: str = ""  # why it FAILED


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
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._state = state_file.load(state_path)
        self._snapshot = self._offer()

    @property
    def snapshot(self) -> Snapshot:
        with self._lock:
            return self._snapshot

    def _set(self, snapshot: Snapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def _offer(self) -> Snapshot:
        release = state_file.visible(self._state, self.current) if self.enabled else None
        return Snapshot(AVAILABLE, release) if release is not None else Snapshot()

    def _busy(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _start(self, work: Callable[[], None]) -> None:
        self._thread = threading.Thread(target=work, daemon=True)
        self._thread.start()

    def _save(self) -> None:
        try:
            state_file.save(self.state_path, self._state)
        except OSError:
            pass

    def check(self, force: bool = False) -> None:
        """Ask GitHub in the background when enabled and a week has passed, or when forced
        (a settings screen was opened)."""
        if not self.enabled or self._busy():
            return
        if not force and not state_file.is_due(self._state, self._clock()):
            return
        self._start(self._check)

    def _check(self) -> None:
        try:
            found = newest(self._fetch(), self.product, self.current)
        except UpdateError:
            return  # offline or rate limited: stay quiet and try again next launch
        self._state = replace(self._state, last_check=self._clock(), found=found)
        self._save()
        if self.snapshot.status in (IDLE, AVAILABLE):
            self._set(self._offer())

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if self.snapshot.status in (IDLE, AVAILABLE):
            self._set(self._offer())
        if enabled:
            self.check()

    def dismiss(self) -> None:
        """Hide the offered version until a newer one appears."""
        snap = self.snapshot
        if snap.release is None or snap.status not in (AVAILABLE, FAILED):
            return
        self._state = replace(self._state, dismissed=snap.release.version)
        self._save()
        self._set(Snapshot())

    def install(self, installer: Installer) -> None:
        """Run installer(release, progress) in the background for the offered release."""
        snap = self.snapshot
        if snap.release is None or snap.status not in (AVAILABLE, FAILED) or self._busy():
            return
        release = snap.release
        self._set(Snapshot(DOWNLOADING, release))

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
            self._set(Snapshot(READY, release))

        self._start(work)

    def wait(self, timeout: Optional[float] = None) -> None:
        """Wait for background work to finish."""
        if self._thread is not None:
            self._thread.join(timeout)


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
