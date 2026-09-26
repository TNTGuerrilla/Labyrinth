"""Entry point: python -m maze_saver [/s | /c[:hwnd] | /p <hwnd> | --window] [--multiwindow]."""
from __future__ import annotations

import os
import sys
import traceback
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


def _run(argv: Sequence[str]) -> None:
    command = parse_args(argv)
    if command.mode == "none":
        return
    if command.mode == "config":
        from .settings_dialog import run_dialog
        run_dialog(command.hwnd)
        return
    from . import app
    settings = config.load()
    if command.mode == "saver":
        app.run_saver(settings, command.multiwindow)
    elif command.mode == "preview":
        app.run_preview(command.hwnd, settings)
    elif command.mode == "window":
        app.run_debug_window(settings)


def main(argv: Optional[Sequence[str]] = None) -> None:
    try:
        _run(sys.argv[1:] if argv is None else argv)
    except Exception:
        _log_error()
        raise


if __name__ == "__main__":
    main()
