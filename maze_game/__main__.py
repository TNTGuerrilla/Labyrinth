"""Entry point: python -m maze_game."""
from __future__ import annotations

import os
import traceback

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

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

        from maze_saver import monitors

        from . import app
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
