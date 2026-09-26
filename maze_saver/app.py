"""Windows, the main loop, and the run modes (screensaver, preview, debug window)."""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Optional, Sequence

import pygame

from . import monitors
from .board import FIRST_DELAY_MAX, Board
from .config import Settings
from .input_watch import ExitWatcher
from .layout import Layout, Monitor, Rect, plan_layout, scale_to_fit
from .render import BLACK, BoardRenderer

TITLE = "Maze Screensaver"
MUTEX_NAME = "Local\\MazeScreensaver"
MULTIWINDOW_FPS_MAX = 60
PREVIEW_FPS = 30
DEBUG_FPS = 60
DEBUG_WINDOW_MAX = (1600, 900)
DEBUG_GAP_COLOR = (24, 24, 24)
DISPLAY_POLL_SECONDS = 2.0
EXIT_EVENTS = frozenset({pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL, pygame.QUIT,
                         pygame.WINDOWCLOSE})


@dataclass
class Slot:
    board: Board
    renderer: BoardRenderer
    offset: tuple[int, int]  # board surface position inside its window surface
    window: Optional["pygame.Window"] = None  # set in multi-window mode


def make_slots(surface: pygame.Surface, rects: Sequence[Rect], settings: Settings,
               rng: random.Random, first_cycle: bool) -> list[Slot]:
    """One board per rect; rects are in `surface` coordinates."""
    slots = []
    for r in rects:
        sub = surface.subsurface(pygame.Rect(r.x, r.y, r.w, r.h))
        delay = rng.uniform(0.0, FIRST_DELAY_MAX) if first_cycle else 0.0
        slots.append(Slot(Board(r.w, r.h, settings, rng, delay), BoardRenderer(sub), (r.x, r.y)))
    return slots


class Stage:
    """The open window(s) for one layout and the boards drawn into them."""

    def __init__(self, slots: Sequence[Slot], fps: int):
        self.slots = list(slots)
        self.fps = fps

    def frame(self, dt: float) -> None:
        display_rects = []
        for slot in self.slots:
            rects = slot.renderer.apply(slot.board, slot.board.update(dt))
            if not rects:
                continue
            if slot.window is not None:
                slot.window.flip()
            else:
                ox, oy = slot.offset
                display_rects.extend(r.move(ox, oy) for r in rects)
        if display_rects:
            pygame.display.update(display_rects)

    def close(self) -> None:
        for slot in self.slots:
            if slot.window is not None:
                slot.window.destroy()


def _open_single(layout: Layout, settings: Settings, rng: random.Random, first_cycle: bool) -> Stage:
    win = layout.window
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{win.x},{win.y}"
    surface = pygame.display.set_mode((win.w, win.h), pygame.NOFRAME)
    pygame.display.set_caption(TITLE)
    hwnd = pygame.display.get_wm_info()["window"]
    monitors.set_topmost(hwnd, win.x, win.y, win.w, win.h)
    monitors.bring_to_foreground(hwnd)
    surface.fill(BLACK)
    pygame.display.flip()
    rects = [r.moved(-win.x, -win.y) for r in layout.boards]
    return Stage(make_slots(surface, rects, settings, rng, first_cycle), layout.fps)


def _open_multi(layout: Layout, settings: Settings, rng: random.Random, first_cycle: bool) -> Stage:
    slots = []
    for r in layout.boards:
        window = pygame.Window(TITLE, (r.w, r.h), (r.x, r.y), borderless=True, always_on_top=True)
        monitors.set_topmost(window.handle, r.x, r.y, r.w, r.h)
        surface = window.get_surface()
        surface.fill(BLACK)
        window.flip()
        slot = make_slots(surface, [Rect(0, 0, r.w, r.h)], settings, rng, first_cycle)[0]
        slot.window = window
        slots.append(slot)
    slots[0].window.focus()
    monitors.bring_to_foreground(slots[0].window.handle)
    return Stage(slots, min(layout.fps, MULTIWINDOW_FPS_MAX))


def open_stage(monitor_list: Sequence[Monitor], settings: Settings, rng: random.Random,
               force_multiwindow: bool, first_cycle: bool) -> Stage:
    layout = plan_layout(monitor_list, settings.fps_cap, force_multiwindow)
    opener = _open_multi if layout.multiwindow else _open_single
    return opener(layout, settings, rng, first_cycle)


def needs_rebuild(opened_signature: tuple[int, int, int, int, int],
                  current_signature: tuple[int, int, int, int, int]) -> bool:
    """True when the virtual screen signature has changed since the stage was opened,
    meaning a monitor was added/removed/rearranged and the stage must be rebuilt."""
    return opened_signature != current_signature


def run_saver(settings: Settings, force_multiwindow: bool = False) -> None:
    monitors.enable_dpi_awareness()
    mutex = monitors.acquire_single_instance(MUTEX_NAME)
    if mutex is None:
        return
    try:
        monitors.set_below_normal_priority()
        pygame.display.init()
        rng = random.Random()
        current = monitors.get_monitors()
        stage = open_stage(current, settings, rng, force_multiwindow, first_cycle=True)
        pygame.mouse.set_visible(False)
        clock = pygame.time.Clock()
        watcher = ExitWatcher(time.monotonic(), monitors.cursor_pos())
        signature = monitors.virtual_screen_signature()
        next_poll = time.monotonic() + DISPLAY_POLL_SECONDS

        def rebuild() -> None:
            nonlocal stage, watcher, signature, current
            fresh = monitors.get_monitors()
            if fresh:
                current = fresh
            stage.close()
            pygame.display.quit()
            pygame.display.init()
            stage = open_stage(current, settings, rng, force_multiwindow, first_cycle=False)
            pygame.mouse.set_visible(False)
            watcher = ExitWatcher(time.monotonic(), monitors.cursor_pos())
            signature = monitors.virtual_screen_signature()

        while True:
            dt = clock.tick(stage.fps) / 1000.0
            input_event = any(e.type in EXIT_EVENTS for e in pygame.event.get())
            now = time.monotonic()
            if needs_rebuild(signature, monitors.virtual_screen_signature()):
                rebuild()
            elif watcher.should_exit(now, monitors.cursor_pos(), input_event):
                break
            if now >= next_poll:
                next_poll = now + DISPLAY_POLL_SECONDS
                latest = monitors.get_monitors()
                if latest and latest != current:
                    current = latest
                    rebuild()
            stage.frame(dt)
    finally:
        pygame.quit()
        monitors.release_handle(mutex)


def run_preview(hwnd: int, settings: Settings) -> None:
    """Render one board into the Screen Saver Settings preview box until it closes."""
    if not monitors.is_window(hwnd):
        return
    monitors.enable_dpi_awareness()
    os.environ["SDL_WINDOWID"] = str(hwnd)
    pygame.display.init()
    try:
        w, h = monitors.client_size(hwnd)
        w, h = max(1, w), max(1, h)
        surface = pygame.display.set_mode((w, h))
        stage = Stage(make_slots(surface, [Rect(0, 0, w, h)], settings, random.Random(), False),
                      PREVIEW_FPS)
        clock = pygame.time.Clock()
        while monitors.is_window(hwnd):
            dt = clock.tick(stage.fps) / 1000.0
            pygame.event.get()
            stage.frame(dt)
    finally:
        pygame.quit()


def run_debug_window(settings: Settings) -> None:
    """A scaled-down copy of the real monitor layout in a normal window."""
    monitors.enable_dpi_awareness()
    pygame.display.init()
    try:
        size, rects = scale_to_fit(monitors.get_monitors(), *DEBUG_WINDOW_MAX)
        surface = pygame.display.set_mode(size)
        pygame.display.set_caption(f"{TITLE} (debug)")
        surface.fill(DEBUG_GAP_COLOR)
        pygame.display.flip()
        stage = Stage(make_slots(surface, rects, settings, random.Random(), True), DEBUG_FPS)
        clock = pygame.time.Clock()
        while True:
            dt = clock.tick(stage.fps) / 1000.0
            events = pygame.event.get()
            if any(e.type in (pygame.QUIT, pygame.WINDOWCLOSE)
                   or (e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE) for e in events):
                break
            stage.frame(dt)
    finally:
        pygame.quit()
