"""Entry point: python -m maze_saver [/s | /c[:hwnd] | /p <hwnd> | --window] [--multiwindow]."""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Sequence

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from . import config  # noqa: E402
from .cli import parse_args  # noqa: E402


def _log_error() -> None:
    """The built .scr has no console, so unexpected errors go to a log file."""
    try:
        path = config.default_path().with_name("error.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
    except OSError:
        pass


def _updater(settings: config.Settings):
    """The update checker for a built screensaver, or None when running from source."""
    from labyrinth_update.releases import SCREENSAVER
    from labyrinth_update.updater import for_program
    return for_program(SCREENSAVER, config.default_path().parent, settings.check_updates)


def _notice(updater):
    """What the running screensaver shows about an update: a function the render loop
    polls, since the check finishes in the background after the screensaver starts."""
    if updater is None:
        return None
    from labyrinth_update.updater import AVAILABLE
    updater.check()

    def notice():
        snap = updater.snapshot
        if snap.status != AVAILABLE:
            return None
        return (f"Labyrinth Screensaver {snap.release.version} is available. "
                "Open Screen Saver Settings to update.")

    return notice


def _whats_new(updater):
    """The What's new section for the first runs of a newer version, or None."""
    if updater is None:
        return None
    shown = updater.start_whats_new()
    if shown is None:
        return None
    # Counted before anything is shown: any key or mouse move ends the screensaver, and an
    # interrupted run must still count toward the limit of SHOW_RUNS.
    updater.count_whats_new_run()
    from .app import SaverWhatsNew
    return SaverWhatsNew(f"Labyrinth Screensaver updated to {shown.version}",
                         tuple(shown.lines()), updater.mark_whats_new_seen)


def _run(argv: Sequence[str]) -> None:
    command = parse_args(argv)
    if command.mode == "none":
        return
    if command.mode == "apply":
        from labyrinth_update.install import apply_update
        staged, target, sha256 = command.update_args
        sys.exit(apply_update(Path(staged), Path(target), sha256))
    if command.mode == "config":
        from .settings_dialog import run_dialog
        run_dialog(command.hwnd, updater=_updater(config.load()))
        return
    from . import app
    settings = config.load()
    if command.mode == "saver":
        updater = _updater(settings)
        whats_new = _whats_new(updater)
        app.run_saver(settings, command.multiwindow, command.leads,
                      notice=_notice(updater), whats_new=whats_new)
    elif command.mode == "preview":
        app.run_preview(command.hwnd, settings)
    elif command.mode == "window":
        app.run_debug_window(settings, command.leads)


def main(argv: Optional[Sequence[str]] = None) -> None:
    try:
        _run(sys.argv[1:] if argv is None else argv)
    except Exception:
        _log_error()
        raise


if __name__ == "__main__":
    main()
