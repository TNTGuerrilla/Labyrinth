"""The Labyrinth icon for window title bars and taskbars (made by tools/make_icons.py)."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    import pygame

# The tkinter Settings dialog reads ICON_PATH too, so pygame is imported only when used.
ICON_PATH = Path(__file__).parent / "assets" / "icon.png"


def load_icon() -> Optional[pygame.Surface]:
    """The icon, or None if it cannot be read: a window without an icon still works."""
    import pygame
    try:
        return pygame.image.load(str(ICON_PATH))
    except (pygame.error, OSError):
        return None


def set_display_icon() -> None:
    """Give the pygame.display window the icon. Call before pygame.display.set_mode()."""
    import pygame
    icon = load_icon()
    if icon is not None:
        pygame.display.set_icon(icon)
