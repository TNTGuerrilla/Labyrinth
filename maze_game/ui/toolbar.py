"""The strip of buttons along the top of the window."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from ..keymap import LABELS, Keymap, key_label
from .widgets import (BAR_BG, BORDER, Hits, button_rect, draw_button, draw_panel,
                      draw_split_button, font, format_time, text)

TOOLBAR_H = 40
UPDATE_SIZE = 15


def split_width(label: str, dismiss: bool) -> int:
    width = button_rect(label, (0, 0), size=UPDATE_SIZE).w
    return width + (button_rect("x", (0, 0), size=UPDATE_SIZE).w if dismiss else 0)


def split_rects(label: str, right: int,
                dismiss: bool) -> tuple[pygame.Rect, Optional[pygame.Rect]]:
    """The install part and the x part of the update control, whose right edge is `right`.
    The two share an edge, where the divider is drawn."""
    close = (button_rect("x", (right, 6), size=UPDATE_SIZE, anchor="topright")
             if dismiss else None)
    main = button_rect(label, (close.x if close is not None else right, 6), size=UPDATE_SIZE,
                       anchor="topright")
    return main, close


ITEMS = (
    ("new", "New maze"), ("replay", "Replay"), ("hint", "Hint"), ("autosolve", "Auto-solve"),
    ("flash", "Flash finish"), None,
    ("small", "S"), ("medium", "M"), ("large", "L"), ("xl", "XL"), ("custom", "Custom"), None,
    ("colors", "Colors"), ("settings", "Settings"),
)
TIP_NAMES = {"small": "Small (8-12)", "medium": "Medium (13-24)", "large": "Large (25-48)",
             "xl": "XL (49-96)", "custom": "Custom size"}


@dataclass(frozen=True)
class ToolbarState:
    difficulty: str
    autosolve: bool
    multicolor: bool
    explored: int
    elapsed: float
    update_label: Optional[str] = None  # None hides the update button
    update_short: str = ""  # the label when the window is too narrow for update_label
    update_tip: str = ""
    update_dismiss: bool = False  # show the x that hides this version


class Toolbar:
    def __init__(self):
        self.hits = Hits()

    def draw(self, surface: pygame.Surface, keymap: Keymap, state: ToolbarState,
             mouse: tuple[int, int]) -> None:
        width = surface.get_width()
        surface.fill(BAR_BG, (0, 0, width, TOOLBAR_H))
        pygame.draw.line(surface, BORDER, (0, TOOLBAR_H - 1), (width, TOOLBAR_H - 1))
        self.hits.clear()
        x = 8
        tip = None
        for item in ITEMS:
            if item is None:
                x += 14
                continue
            action, label = item
            rect = button_rect(label, (x, 6), size=15)
            active = (action == state.difficulty
                      or (action == "autosolve" and state.autosolve)
                      or (action == "colors" and state.multicolor))
            hovered = rect.collidepoint(mouse)
            draw_button(surface, rect, label, size=15, active=active, hovered=hovered)
            self.hits.add(rect, action)
            if hovered:
                tip = action
            x = rect.right + 6
        stats = f"Explored {state.explored}     Time {format_time(state.elapsed)}"
        if state.update_label is None:
            text(surface, stats, (width - 12, TOOLBAR_H // 2), 15, anchor="midright")
        else:
            hovered = self._draw_update(surface, state, stats, x, mouse)
            if hovered is not None:
                tip = hovered
        if tip is not None:
            self._tooltip(surface, keymap, state, tip, mouse)

    def _draw_update(self, surface: pygame.Surface, state: ToolbarState, stats: str,
                     left_end: int, mouse: tuple[int, int]) -> Optional[str]:
        """The update control just left of the counters: one split button, install on the
        left and (when this version can be hidden) x on the right. A narrow window gets the
        short label, then compact counters, then no counters. Returns the hovered action."""
        width = surface.get_width()
        compact = f"{state.explored}   {format_time(state.elapsed)}"
        choices = ((state.update_label, stats), (state.update_short, stats),
                   (state.update_short, compact), (state.update_short, ""))
        for label, info in choices:
            info_w = font(15).size(info)[0] + 12 if info else 0
            if width - 12 - info_w - split_width(label, state.update_dismiss) >= left_end + 8:
                break
        right = width - 12
        if info:
            text(surface, info, (right, TOOLBAR_H // 2), 15, anchor="midright")
            right -= info_w
        main, close = split_rects(label, right, state.update_dismiss)
        over_main = main.collidepoint(mouse)
        over_close = close is not None and close.collidepoint(mouse)
        draw_split_button(surface, main, close, label, over_main, over_close, UPDATE_SIZE)
        self.hits.add(main, "update")
        if close is not None:
            self.hits.add(close, "update_dismiss")
        return "update" if over_main else "update_dismiss" if over_close else None

    def _tooltip(self, surface: pygame.Surface, keymap: Keymap, state: ToolbarState,
                 action: str, mouse: tuple[int, int]) -> None:
        if action == "update":
            label = state.update_tip
        elif action == "update_dismiss":
            label = "Hide until the next version"
        else:
            name = TIP_NAMES.get(action, LABELS[action])
            label = f"{name} ({key_label(keymap.keys_for(action)[0])})"
        if not label:
            return
        width = font(14).size(label)[0] + 16
        box = pygame.Rect(min(mouse[0], surface.get_width() - width - 4), TOOLBAR_H + 4, width, 24)
        draw_panel(surface, box)
        text(surface, label, box.center, 14, anchor="center")

    def action_at(self, pos: tuple[int, int]) -> Optional[str]:
        return self.hits.at(pos)
