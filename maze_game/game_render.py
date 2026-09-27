"""Draws a Round through a Camera.

Cells go into an off-screen layer the size of the play area. Each frame the layer is
blitted to the window and overlays (dot, hint glow, finish flash, win pulse) are drawn
on top, so overlays never cost cell redraws. Cell drawing is spread across frames with
a time budget, so no frame stalls however large the maze is: a zoom or resize shows
the old image stretched to the new scale and sharpens it over the following frames.
"""
from __future__ import annotations

import math
import time
from collections import deque
from typing import Callable, Iterator, Optional

import pygame

from maze_saver.maze import DELTAS, Cell, edge_key, step
from maze_saver.render import (BLACK, DOT_AT_END_SCALE, END_COLOR, MARKER_RADIUS, START_COLOR,
                               TRAIL_COLOR, TRAIL_DIM_COLOR, cached_palette, draw_cell, spoke)

from .camera import Camera
from .round import FLASH_SECONDS, HINT_SECONDS, WIN_PULSE_SECONDS

REDRAW_BUDGET = 0.008  # seconds of cell drawing per frame
CHECK_EVERY = 32  # cells drawn between clock checks
LOW_DETAIL_PX = 4
MIN_MARKER_PX = 3
HINT_COLOR = (120, 200, 255)
WHITE = (255, 255, 255)
ARROW_INSET = 28
ARROW_SIZE = 14

View = tuple[int, tuple[int, int]]  # (cell_px, origin) the layer currently shows


def _scale(color: tuple, k: float) -> tuple:
    k = max(0.0, min(1.0, k))
    return tuple(int(ch * k) for ch in color)


def _mix(a: tuple, b: tuple, k: float) -> tuple:
    return tuple(int(x + (y - x) * k) for x, y in zip(a, b))


def draw_cell_small(surface: pygame.Surface, board, c: Cell, rect: pygame.Rect,
                    palettes: dict) -> None:
    """Low-detail cell for tiny cells: 1 px pipes in the stripe color, trail colors."""
    surface.fill(BLACK, rect)
    region = board.region_of.get(c)
    if region is None:
        return
    base = cached_palette(palettes, board.hues[region])[1]
    bits = board.grid.open_dirs(c)
    hub = base
    for d in DELTAS:
        if not bits & d:
            continue
        state = board.trail.get(edge_key(c, step(c, d)))
        if state is None:
            color = base
        else:
            color = TRAIL_COLOR if state else TRAIL_DIM_COLOR
            if state or hub is base:
                hub = color
        surface.fill(color, spoke(rect, d, 1))
    surface.fill(hub, (rect.centerx, rect.centery, 1, 1))


class GameRenderer:
    def __init__(self, size: tuple[int, int], clock: Callable[[], float] = time.perf_counter):
        self.layer = pygame.Surface(size)
        self.layer.fill(BLACK)
        self._clock = clock
        self._palettes: dict = {}
        self._view: Optional[View] = None
        self._clear = True
        self._source: Optional[pygame.Surface] = None
        self._queue: deque = deque()
        self._queued: set = set()
        self._sweep: Optional[Iterator[Cell]] = None

    @property
    def pending(self) -> bool:
        return bool(self._queue) or self._sweep is not None

    def invalidate(self, clear: bool = True) -> None:
        """Redraw everything. clear=False keeps the old image until the sweep reaches it."""
        self._view = None
        self._clear = clear
        self._source = None

    def resize(self, size: tuple[int, int]) -> None:
        if self._view is not None and self._source is None:
            self._source = self.layer
        self.layer = pygame.Surface(size)
        self.layer.fill(BLACK)

    def render(self, screen: pygame.Surface, play_rect: pygame.Rect, board, camera: Camera,
               changed: set) -> None:
        view = (camera.cell_px, camera.origin())
        for c in changed:
            self._enqueue(c)
        if self._view is None:
            if self._clear:
                self.layer.fill(BLACK)
            self._sweep = camera.visible_cells()
        elif self._source is not None or view[0] != self._view[0]:
            source = self._source if self._source is not None else self.layer
            self._stretch(source, self._view, view)
            self._sweep = camera.visible_cells()
        elif view[1] != self._view[1]:
            self._scroll(camera, view[1][0] - self._view[1][0], view[1][1] - self._view[1][1])
        self._view = view
        self._source = None
        self._drain(board, camera)
        screen.blit(self.layer, play_rect.topleft)
        old_clip = screen.get_clip()
        screen.set_clip(play_rect)
        draw_overlays(screen, play_rect, board, camera)
        screen.set_clip(old_clip)

    def _enqueue(self, c: Cell) -> None:
        if c not in self._queued:
            self._queued.add(c)
            self._queue.append(c)

    def _drain(self, board, camera: Camera) -> None:
        deadline = self._clock() + REDRAW_BUDGET
        count = 0
        while self._queue or self._sweep is not None:
            if self._queue:
                c = self._queue.popleft()
                self._queued.discard(c)
            else:
                c = next(self._sweep, None)
                if c is None:
                    self._sweep = None
                    return
            self._draw(board, camera, c)
            count += 1
            if count % CHECK_EVERY == 0 and self._clock() >= deadline:
                return

    def _draw(self, board, camera: Camera, c: Cell) -> None:
        x, y, w, h = camera.cell_rect(c)
        lw, lh = self.layer.get_size()
        if x >= lw or y >= lh or x + w <= 0 or y + h <= 0:
            return
        rect = pygame.Rect(x, y, w, h)
        if w >= LOW_DETAIL_PX:
            draw_cell(self.layer, board, c, rect, self._palettes, draw_dot=False)
        else:
            draw_cell_small(self.layer, board, c, rect, self._palettes)

    def _scroll(self, camera: Camera, dx: int, dy: int) -> None:
        w, h = self.layer.get_size()
        if abs(dx) >= w or abs(dy) >= h:
            self.layer.fill(BLACK)
            self._sweep = camera.visible_cells()
            return
        self.layer.scroll(dx, dy)
        strips = []
        if dx > 0:
            strips.append((0, 0, dx, h))
        elif dx < 0:
            strips.append((w + dx, 0, -dx, h))
        if dy > 0:
            strips.append((0, 0, w, dy))
        elif dy < 0:
            strips.append((0, h + dy, w, -dy))
        for sx, sy, sw, sh in strips:
            self.layer.fill(BLACK, (sx, sy, sw, sh))
            x0, y0, x1, y1 = camera.cells_in_rect(sx, sy, sw, sh)
            for cy in range(y0, y1):
                for cx in range(x0, x1):
                    self._enqueue((cx, cy))

    def _stretch(self, source: pygame.Surface, old: View, new: View) -> None:
        """Scale the part of `source` still in view into a fresh layer: a quick preview
        until the sweep redraws the cells sharply."""
        old_px, (oox, ooy) = old
        new_px, (nox, noy) = new
        k = new_px / old_px
        target = pygame.Surface(self.layer.get_size())
        target.fill(BLACK)
        sw, sh = source.get_size()
        tw, th = target.get_size()
        # A source pixel s lands at target pixel (s - old_origin) * k + new_origin.
        x0 = max(0.0, oox - nox / k)
        y0 = max(0.0, ooy - noy / k)
        x1 = min(float(sw), oox + (tw - nox) / k)
        y1 = min(float(sh), ooy + (th - noy) / k)
        if x1 - x0 >= 1 and y1 - y0 >= 1:
            src = pygame.Rect(int(x0), int(y0), max(1, int(x1) - int(x0)),
                              max(1, int(y1) - int(y0)))
            size = (max(1, round(src.w * k)), max(1, round(src.h * k)))
            scaled = pygame.transform.scale(source.subsurface(src), size)
            target.blit(scaled, (round((src.x - oox) * k + nox), round((src.y - ooy) * k + noy)))
        self.layer = target


def draw_overlays(screen: pygame.Surface, play_rect: pygame.Rect, board, camera: Camera) -> None:
    px = camera.cell_px
    ox, oy = play_rect.topleft

    def at(pos: tuple[float, float]) -> tuple[int, int]:
        sx, sy = camera.to_screen(*pos)
        return (round(ox + sx), round(oy + sy))

    def center(c: Cell) -> tuple[int, int]:
        return at((c[0] + 0.5, c[1] + 0.5))

    radius = max(MIN_MARKER_PX, round(px * MARKER_RADIUS))
    if px < LOW_DETAIL_PX:
        pygame.draw.circle(screen, END_COLOR, center(board.end), radius)
        width = 0 if board.dot == board.start else 1
        pygame.draw.circle(screen, START_COLOR, center(board.start), radius, width)
    if board.hint_active:
        age = board.time - board.hint_at
        fade = 1.0 - age / HINT_SECONDS
        pulse = 0.65 + 0.35 * math.sin(age * math.tau * 2)
        color = _scale(HINT_COLOR, fade * pulse)
        ring = max(2, round(px * 0.42))
        for c in board.hint_route:
            pygame.draw.circle(screen, color, center(c), ring, max(1, px // 8))
    if board.win_pulse_active:
        b = math.sin(math.pi * min(1.0, (board.time - board.won_at) / WIN_PULSE_SECONDS))
        color = _mix(TRAIL_COLOR, WHITE, b)
        size = max(1, round(px * 0.2 * (1 + b)))
        for c in board.path.route:
            pos = center(c)
            if play_rect.collidepoint(pos):
                pygame.draw.circle(screen, color, pos, size)
    if board.flash_active:
        t = (board.time - board.flash_at) / FLASH_SECONDS
        end = center(board.end)
        reach = max(px * 2.5, 36)
        for i in range(3):
            phase = (t * 2 + i / 3) % 1.0
            pygame.draw.circle(screen, _scale(END_COLOR, (1 - phase) * (1 - t)), end,
                               round(radius + phase * reach), 2)
        if not play_rect.collidepoint(end):
            _draw_arrow(screen, play_rect, end, _scale(END_COLOR, 1 - t * 0.5))
    dot_radius = radius
    if board.dot == board.end and not board.mover.moving:
        dot_radius = max(1, round(radius * DOT_AT_END_SCALE))
    pygame.draw.circle(screen, START_COLOR, at(board.mover.position()), dot_radius)


def _draw_arrow(screen: pygame.Surface, area: pygame.Rect, target: tuple[int, int],
                color: tuple) -> None:
    """A triangle at the edge of `area` pointing from its center toward `target`."""
    cx, cy = area.center
    vx, vy = target[0] - cx, target[1] - cy
    length = math.hypot(vx, vy)
    if length == 0:
        return
    ux, uy = vx / length, vy / length
    hw, hh = area.w / 2 - ARROW_INSET, area.h / 2 - ARROW_INSET
    reach = min(hw / abs(ux) if ux else math.inf, hh / abs(uy) if uy else math.inf)
    tip = (cx + ux * reach, cy + uy * reach)
    base = (tip[0] - ux * ARROW_SIZE * 1.6, tip[1] - uy * ARROW_SIZE * 1.6)
    left = (base[0] - uy * ARROW_SIZE, base[1] + ux * ARROW_SIZE)
    right = (base[0] + uy * ARROW_SIZE, base[1] - ux * ARROW_SIZE)
    pygame.draw.polygon(screen, color, [tip, left, right])
