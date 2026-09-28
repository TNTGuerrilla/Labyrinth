"""Entry point: python -m maze_game."""
from __future__ import annotations

import os
import sys
import traceback

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
# On Linux the window class must match the installed .desktop file, so desktops show its icon.
APP_ID = "com.bydesigninteractive.labyrinth"
os.environ.setdefault("SDL_VIDEO_X11_WMCLASS", APP_ID)
os.environ.setdefault("SDL_VIDEO_WAYLAND_WMCLASS", APP_ID)

from . import config  # noqa: E402


def _log_error() -> None:
    """The built exe has no console, so unexpected errors go to a log file."""
    try:
        path = config.default_path().with_name("error.log")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(traceback.format_exc() + "\n")
    except OSError:
        pass


def _valid_key(name: str) -> bool:
    import pygame
    try:
        pygame.key.key_code(name)
    except ValueError:
        return False
    return True


def main() -> None:
    try:
        import pygame

        from . import app
        if sys.platform == "win32":
            from maze_saver import monitors
            monitors.enable_dpi_awareness()
        pygame.init()
        try:
            settings, keymap = config.load(valid_key=_valid_key)
            app.run(settings, keymap)
        finally:
            pygame.quit()
    except Exception:
        _log_error()
        raise


if __name__ == "__main__":
    main()
