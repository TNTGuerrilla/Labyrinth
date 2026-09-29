"""The overlay shown after the dot reaches the finish."""
from __future__ import annotations

from typing import Optional

import pygame

from ..keymap import Keymap, key_label
from .widgets import MUTED, WARN, Hits, button_rect, draw_button, draw_panel, format_time, text


def win_lines(r) -> list[tuple[str, str]]:
    lines = [("Cells explored", str(r.explored)), ("Shortest route", str(r.shortest)),
             ("Efficiency", f"{r.efficiency}%"), ("Time", format_time(r.elapsed)),
             ("Hints used", str(r.hints))]
    if r.assisted:
        lines.append(("Auto-solved cells", str(r.auto_explored)))
    return lines


class WinScreen:
    def __init__(self):
        self.hits = Hits()

    def draw(self, surface: pygame.Surface, area: pygame.Rect, r, keymap: Keymap) -> None:
        lines = win_lines(r)
        box = pygame.Rect(0, 0, 340, 150 + 30 * len(lines))
        box.center = area.center
        draw_panel(surface, box)
        text(surface, "Solved!", (box.centerx, box.y + 30), 30, anchor="center")
        if r.assisted:
            text(surface, "Assisted", (box.centerx, box.y + 58), 15, WARN, anchor="center")
        y = box.y + 76
        for label, value in lines:
            text(surface, label, (box.x + 28, y), 17, MUTED)
            text(surface, value, (box.right - 28, y), 17, anchor="topright")
            y += 30
        self.hits.clear()
        replay = f"Replay ({key_label(keymap.keys_for('replay')[0])})"
        new = f"New maze ({key_label(keymap.keys_for('confirm')[0])})"
        replay_rect = button_rect(replay, (box.centerx - 8, box.bottom - 22), anchor="bottomright")
        new_rect = button_rect(new, (box.centerx + 8, box.bottom - 22), anchor="bottomleft")
        draw_button(surface, replay_rect, replay)
        draw_button(surface, new_rect, new)
        self.hits.add(replay_rect, "replay")
        self.hits.add(new_rect, "new")

    def click(self, pos: tuple[int, int]) -> Optional[str]:
        return self.hits.at(pos)
