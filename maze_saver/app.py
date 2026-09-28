"""Windows, the main loop, and the run modes (screensaver, preview, debug window)."""
from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import pygame

from . import monitors
from .board import FIRST_DELAY_MAX, Board
from .config import Settings
from .icon import load_icon, set_display_icon
from .input_watch import ExitWatcher
from .layout import Layout, Monitor, Rect, plan_layout, scale_to_fit
from .render import BLACK, BoardRenderer
from .watermark import Watermark, primary_index
from .whats_new import SaverWhatsNew, SectionClock
from .whats_new_view import WhatsNewSection

TITLE = "Labyrinth Screensaver"
MUTEX_NAME = "Local\\LabyrinthScreensaver"
MULTIWINDOW_FPS_MAX = 60
PREVIEW_FPS = 30
DEBUG_FPS = 60
DEBUG_WINDOW_MAX = (1600, 900)
DEBUG_GAP_COLOR = (24, 24, 24)
DISPLAY_POLL_SECONDS = 2.0
NOTICE_POLL_SECONDS = 1.0
EXIT_EVENTS = frozenset({pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEWHEEL, pygame.QUIT,
                         pygame.WINDOWCLOSE})


@dataclass
class Slot:
    board: Board
    renderer: BoardRenderer
    offset: tuple[int, int]  # board surface position inside its window surface
    window: Optional["pygame.Window"] = None  # set in multi-window mode


def make_slots(surface: pygame.Surface, rects: Sequence[Rect], settings: Settings,
               rng: random.Random, first_cycle: bool, forced_leads: Optional[int] = None) -> list[Slot]:
    """One board per rect; rects are in `surface` coordinates."""
    slots = []
    for r in rects:
        sub = surface.subsurface(pygame.Rect(r.x, r.y, r.w, r.h))
        delay = rng.uniform(0.0, FIRST_DELAY_MAX) if first_cycle else 0.0
        slots.append(Slot(Board(r.w, r.h, settings, rng, delay, forced_leads), BoardRenderer(sub),
                          (r.x, r.y)))
    return slots


def _maze_area(board: Board) -> Optional[Rect]:
    """The part of the board the watermark keeps to: the area the maze on screen was laid
    out in, or while no maze is on screen (black), the area the next one will use. Never the
    pending area while a maze shows: set_area only takes effect at the next maze, so the
    maze on screen may be bigger (or smaller) than the pending area."""
    area = board.maze_area if board.geometry is not None else board.area
    return None if area is None else Rect(*area)


class Stage:
    """The open window(s) for one layout and the boards drawn into them."""

    def __init__(self, slots: Sequence[Slot], fps: int, primary: int = 0):
        self.slots = list(slots)
        self.fps = fps
        self.primary = primary
        self.watermark: Optional[Watermark] = None
        self.section: Optional[WhatsNewSection] = None
        self._section_done: Optional[Callable[[], None]] = None
        self._solved = 0

    def show_notice(self, message: str, now: float) -> None:
        """Show an update notice on the primary monitor's board from the next frame on."""
        if self.watermark is None and self.slots:
            surface = self.slots[self.primary].renderer.surface
            self.watermark = Watermark(message, surface.get_size(), now)

    def show_section(self, section: WhatsNewSection, on_done: Callable[[], None]) -> None:
        """Lay the primary maze out beside the section from its next maze on (the board is
        still black when this is called at start or after a rebuild) and draw the section
        from the next frame."""
        if not self.slots:
            return
        board = self.slots[self.primary].board
        b = section.split.board
        board.set_area((b.x, b.y, b.w, b.h))  # set_area takes a tuple, the split a Rect
        self.section, self._section_done, self._solved = section, on_done, board.mazes_solved

    def _overlays(self, slot: Slot, changes, now: float) -> list:
        """The section and the watermark on the primary board, drawn after the maze."""
        rects = []
        surface = slot.renderer.surface
        section = self.section
        if section is not None:
            if slot.board.mazes_solved != self._solved:
                self._solved = slot.board.mazes_solved
                section.clock.board_solved(now)
            rects += section.update(surface, now, changes.clear)
            if section.clock.faded(now):
                # The first maze that starts from now on uses the whole monitor; the maze on
                # screen keeps its place, so the board never grows under a visible section.
                slot.board.set_area(None)
                self.section = None
                done, self._section_done = self._section_done, None
                if done is not None:
                    done()
        if self.watermark is not None:
            rects += self.watermark.update(surface, now, changes.clear, _maze_area(slot.board))
        return rects

    def frame(self, dt: float, now: Optional[float] = None) -> None:
        display_rects = []
        for i, slot in enumerate(self.slots):
            changes = slot.board.update(dt)
            rects = slot.renderer.apply(slot.board, changes)
            if i == self.primary and (self.section is not None or self.watermark is not None):
                moment = time.monotonic() if now is None else now
                rects += self._overlays(slot, changes, moment)
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


def _open_single(layout: Layout, settings: Settings, rng: random.Random, first_cycle: bool,
                 forced_leads: Optional[int] = None) -> Stage:
    win = layout.window
    os.environ["SDL_VIDEO_WINDOW_POS"] = f"{win.x},{win.y}"
    set_display_icon()
    surface = pygame.display.set_mode((win.w, win.h), pygame.NOFRAME)
    pygame.display.set_caption(TITLE)
    hwnd = pygame.display.get_wm_info()["window"]
    monitors.set_topmost(hwnd, win.x, win.y, win.w, win.h)
    monitors.bring_to_foreground(hwnd)
    surface.fill(BLACK)
    pygame.display.flip()
    rects = [r.moved(-win.x, -win.y) for r in layout.boards]
    return Stage(make_slots(surface, rects, settings, rng, first_cycle, forced_leads), layout.fps,
                 primary_index(layout.boards))


def _open_multi(layout: Layout, settings: Settings, rng: random.Random, first_cycle: bool,
                forced_leads: Optional[int] = None) -> Stage:
    slots = []
    icon = load_icon()
    for r in layout.boards:
        window = pygame.Window(TITLE, (r.w, r.h), (r.x, r.y), borderless=True, always_on_top=True)
        if icon is not None:
            window.set_icon(icon)
        monitors.set_topmost(window.handle, r.x, r.y, r.w, r.h)
        surface = window.get_surface()
        surface.fill(BLACK)
        window.flip()
        slot = make_slots(surface, [Rect(0, 0, r.w, r.h)], settings, rng, first_cycle,
                          forced_leads)[0]
        slot.window = window
        slots.append(slot)
    slots[0].window.focus()
    monitors.bring_to_foreground(slots[0].window.handle)
    return Stage(slots, min(layout.fps, MULTIWINDOW_FPS_MAX), primary_index(layout.boards))


def open_stage(monitor_list: Sequence[Monitor], settings: Settings, rng: random.Random,
               force_multiwindow: bool, first_cycle: bool,
               forced_leads: Optional[int] = None) -> Stage:
    layout = plan_layout(monitor_list, settings.fps_cap, force_multiwindow)
    opener = _open_multi if layout.multiwindow else _open_single
    return opener(layout, settings, rng, first_cycle, forced_leads)


def needs_rebuild(opened_signature: tuple[int, int, int, int, int],
                  current_signature: tuple[int, int, int, int, int]) -> bool:
    """True when the virtual screen signature has changed since the stage was opened,
    meaning a monitor was added/removed/rearranged and the stage must be rebuilt."""
    return opened_signature != current_signature


def run_saver(settings: Settings, force_multiwindow: bool = False, leads: Optional[int] = None,
             notice: Optional[Callable[[], Optional[str]]] = None,
             whats_new: Optional[SaverWhatsNew] = None) -> None:
    monitors.enable_dpi_awareness()
    mutex = monitors.acquire_single_instance(MUTEX_NAME)
    if mutex is None:
        return
    try:
        monitors.set_below_normal_priority()
        pygame.display.init()
        pygame.font.init()
        rng = random.Random()
        section_clock: Optional[SectionClock] = None
        showing = whats_new is not None

        def seen() -> None:
            nonlocal showing
            showing = False
            whats_new.on_seen()

        def attach(target: Stage) -> None:
            # A rebuild (monitor change) makes new boards: give the new primary board the
            # same split, and keep the clock so the minute is not restarted. The clock starts
            # here, just before the first frame, so a slow window open does not eat into the
            # minute (it would otherwise show 59 first).
            nonlocal section_clock
            if showing and target.slots:
                if section_clock is None:
                    section_clock = SectionClock(time.monotonic())
                size = target.slots[target.primary].renderer.surface.get_size()
                target.show_section(WhatsNewSection(whats_new.title, whats_new.lines,
                                                    section_clock, size), seen)

        current = monitors.get_monitors()
        stage = open_stage(current, settings, rng, force_multiwindow, first_cycle=True, forced_leads=leads)
        attach(stage)
        pygame.mouse.set_visible(False)
        clock = pygame.time.Clock()
        watcher = ExitWatcher(time.monotonic(), monitors.cursor_pos())
        signature = monitors.virtual_screen_signature()
        next_poll = time.monotonic() + DISPLAY_POLL_SECONDS
        next_notice = 0.0

        def rebuild() -> None:
            nonlocal stage, watcher, signature, current
            fresh = monitors.get_monitors()
            if fresh:
                current = fresh
            stage.close()
            pygame.display.quit()
            pygame.display.init()
            stage = open_stage(current, settings, rng, force_multiwindow, first_cycle=False,
                               forced_leads=leads)
            attach(stage)
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
            if notice is not None and stage.watermark is None and now >= next_notice:
                next_notice = now + NOTICE_POLL_SECONDS
                message = notice()
                if message:
                    stage.show_notice(message, now)
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


def run_debug_window(settings: Settings, leads: Optional[int] = None) -> None:
    """A scaled-down copy of the real monitor layout in a normal window."""
    monitors.enable_dpi_awareness()
    pygame.display.init()
    try:
        size, rects = scale_to_fit(monitors.get_monitors(), *DEBUG_WINDOW_MAX)
        set_display_icon()
        surface = pygame.display.set_mode(size)
        pygame.display.set_caption(f"{TITLE} (debug)")
        surface.fill(DEBUG_GAP_COLOR)
        pygame.display.flip()
        stage = Stage(make_slots(surface, rects, settings, random.Random(), True, leads), DEBUG_FPS)
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
