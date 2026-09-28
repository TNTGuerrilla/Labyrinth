"""Draws the Settings panel and turns clicks into SettingsModel calls."""
from __future__ import annotations

from typing import Optional

import pygame

from .settings_model import TABS, SettingsModel
from .widgets import (BORDER, HILITE, LINK, MUTED, TEXT, WARN, Hits, button_rect, dim,
                      draw_button, draw_panel, text)

ROW_H = 30
VALUE_W = 220
INFO_BUTTON_ROWS = ("check_now", "update", "whats_new")


class SettingsPanel:
    def __init__(self, model: SettingsModel):
        self.model = model
        self.hits = Hits()

    @property
    def capturing(self) -> bool:
        return self.model.capturing

    def capture(self, key_name: str) -> None:
        self.model.capture(key_name)

    def handle(self, nav: str, now: float = 0.0) -> Optional[str]:
        return self.model.handle(nav, now)

    def draw(self, surface: pygame.Surface) -> None:
        m = self.model
        dim(surface)
        sw, sh = surface.get_size()
        box = pygame.Rect(0, 0, min(640, sw - 32), min(600, sh - 32))
        box.center = (sw // 2, sh // 2)
        draw_panel(surface, box)
        self.hits.clear()
        x = box.x + 16
        for i, name in enumerate(TABS):
            rect = button_rect(name, (x, box.y + 14))
            draw_button(surface, rect, name, active=(i == m.tab))
            self.hits.add(rect, ("tab", i))
            x = rect.right + 8
        rows = m.rows()
        body = len(rows) - 2
        top = box.y + 58
        footer = box.bottom - 48
        visible = max(1, (footer - 26 - top) // ROW_H)
        first = min(max(0, m.index - visible // 2), max(0, body - visible))
        mouse = pygame.mouse.get_pos()
        for i in range(first, min(body, first + visible)):
            row = rows[i]
            rect = pygame.Rect(box.x + 12, top + (i - first) * ROW_H, box.w - 24, ROW_H - 4)
            if row.kind == "header":
                label = text(surface, row.label.upper(), (rect.x + 4, rect.bottom - 2), 13,
                             MUTED, anchor="bottomleft")
                pygame.draw.line(surface, BORDER, (label.right + 8, label.centery),
                                 (rect.right, label.centery))
                continue
            if row.kind == "info":
                color = TEXT if row.name == "version" else MUTED
                text(surface, row.label, (rect.x + 10, rect.centery), 15, color,
                     anchor="midleft")
                continue  # text only: no highlight and no hit area
            if row.kind == "button" and row.name in INFO_BUTTON_ROWS:
                btn = button_rect(row.label, (rect.x + 10, rect.centery), 15, anchor="midleft")
                draw_button(surface, btn, row.label, 15, active=(i == m.index),
                            hovered=btn.collidepoint(mouse))
                self.hits.add(btn, ("row", i))
                if row.name == "check_now" and m.info.status:
                    text(surface, m.info.status, (btn.right + 10, rect.centery), 15, MUTED,
                         anchor="midleft")
                continue  # a real button, not a highlighted row
            if i == m.index:
                pygame.draw.rect(surface, HILITE, rect, border_radius=4)
            text(surface, row.label, (rect.x + 10, rect.centery), 15, anchor="midleft")
            value = m.value_text(row)
            if row.kind in ("bool", "choice", "number"):
                dec = pygame.Rect(rect.right - VALUE_W, rect.y + 1, 24, rect.h - 2)
                inc = pygame.Rect(rect.right - 28, rect.y + 1, 24, rect.h - 2)
                draw_button(surface, dec, "<", 14)
                draw_button(surface, inc, ">", 14)
                text(surface, value, ((dec.right + inc.left) // 2, rect.centery), 15,
                     anchor="center")
                self.hits.add(dec, ("dec", i))
                self.hits.add(inc, ("inc", i))
            elif value:
                text(surface, value, (rect.right - 10, rect.centery), 15,
                     LINK if row.kind == "link" else MUTED, anchor="midright")
            self.hits.add(rect, ("row", i))
        if m.message:
            text(surface, m.message, (box.x + 20, footer - 22), 14, WARN)
        cancel = button_rect("Cancel", (box.right - 16, box.bottom - 12), anchor="bottomright")
        apply = button_rect("Apply", (cancel.x - 8, box.bottom - 12), anchor="bottomright")
        for rect, label, i in ((apply, "Apply", body), (cancel, "Cancel", body + 1)):
            draw_button(surface, rect, label, active=(m.index == i))
            self.hits.add(rect, ("row", i))

    def click(self, pos: tuple[int, int]) -> Optional[str]:
        hit = self.hits.at(pos)
        if hit is None:
            return None
        kind, i = hit
        m = self.model
        if kind == "tab":
            m.set_tab(i)
            return None
        if m.pending_swap is not None:
            return None
        m.select(i)
        if kind == "dec":
            m.change(-1)
            return None
        if kind == "inc":
            m.change(1)
            return None
        return m.activate()
