"""The strip of buttons along the top of the window."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from ..keymap import LABELS, Keymap, key_label
from .widgets import (BAR_BG, BORDER, Hits, button_rect, draw_button, draw_panel, font,
                      format_time, text)

TOOLBAR_H = 40
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
    steps: int
    elapsed: float


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
        text(surface, f"Steps {state.steps}     Time {format_time(state.elapsed)}",
             (width - 12, TOOLBAR_H // 2), 15, anchor="midright")
        if tip is not None:
            self._tooltip(surface, keymap, tip, mouse)

    def _tooltip(self, surface: pygame.Surface, keymap: Keymap, action: str,
                 mouse: tuple[int, int]) -> None:
        name = TIP_NAMES.get(action, LABELS[action])
        label = f"{name} ({key_label(keymap.keys_for(action)[0])})"
        width = font(14).size(label)[0] + 16
        box = pygame.Rect(min(mouse[0], surface.get_width() - width - 4), TOOLBAR_H + 4, width, 24)
        draw_panel(surface, box)
        text(surface, label, box.center, 14, anchor="center")

    def action_at(self, pos: tuple[int, int]) -> Optional[str]:
        return self.hits.at(pos)
