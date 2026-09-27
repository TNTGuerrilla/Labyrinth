"""Draws a Board's changed cells onto a pygame surface.

Each cell is redrawn from scratch: half-pipes ("spokes") run from the cell's
center to the middle of each open side, so neighboring cells join seamlessly.
draw_cell() is shared with the game, which draws into its own rectangles.
"""
from __future__ import annotations

import colorsys

import pygame

from .board import Board, Changes
from .maze import DELTAS, E, N, S, W, Cell, edge_key, step

BLACK = (0, 0, 0)
START_COLOR = (60, 220, 90)
END_COLOR = (235, 64, 64)
TRAIL_COLOR = (255, 240, 205)
TRAIL_DIM_COLOR = (80, 80, 80)
WELD_COLOR = (255, 255, 255)

PIPE_WIDTH = 0.40  # fraction of the cell size
STRIPE_RATIO = 1 / 3  # fraction of the pipe width
TRAIL_WIDTH = 0.15
MARKER_RADIUS = 0.275
DOT_AT_END_SCALE = 0.7


def _hsv(h: float, s: float, v: float) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def palette(hue: float) -> tuple[tuple[int, int, int], ...]:
    """(outer pipe, center stripe, growing head) colors for a hue."""
    return (_hsv(hue, 0.60, 0.55), _hsv(hue, 0.40, 0.85), _hsv(hue, 0.25, 1.0))


def cached_palette(cache: dict, hue: float) -> tuple:
    colors = cache.get(hue)
    if colors is None:
        colors = cache[hue] = palette(hue)
    return colors


def spoke(rect: pygame.Rect, d: int, width: int) -> pygame.Rect:
    cx, cy = rect.center
    half = width // 2
    if d == N:
        return pygame.Rect(cx - half, rect.top, width, cy - rect.top)
    if d == S:
        return pygame.Rect(cx - half, cy, width, rect.bottom - cy)
    if d == W:
        return pygame.Rect(rect.left, cy - half, cx - rect.left, width)
    return pygame.Rect(cx, cy - half, rect.right - cx, width)


def draw_cell(surface: pygame.Surface, board, c: Cell, rect: pygame.Rect, palettes: dict,
              draw_dot: bool = True) -> None:
    """Redraw one cell from scratch into `rect`. `board` is anything with the Board
    attributes grid, region_of, hues, welds, trail, head_cells, start, end and dot."""
    surface.fill(BLACK, rect)
    region = board.region_of.get(c)
    if region is not None:
        _draw_pipe(surface, board, c, rect, cached_palette(palettes, board.hues[region]))
    _draw_trail(surface, board, c, rect)
    _draw_markers(surface, board, c, rect, draw_dot)


def _draw_pipe(surf: pygame.Surface, board, c: Cell, rect: pygame.Rect, colors: tuple) -> None:
    outer, stripe, head = colors
    size = rect.w
    pipe_w = max(2, round(size * PIPE_WIDTH))
    stripe_w = max(1, round(pipe_w * STRIPE_RATIO))
    bits = board.grid.open_dirs(c)
    dirs = [d for d in DELTAS if bits & d]
    welding = {d for d in dirs if edge_key(c, step(c, d)) in board.welds}
    for d in dirs:
        surf.fill(WELD_COLOR if d in welding else outer, spoke(rect, d, pipe_w))
    pygame.draw.circle(surf, outer, rect.center, pipe_w // 2)
    for d in dirs:
        if d not in welding:
            surf.fill(stripe, spoke(rect, d, stripe_w))
    pygame.draw.circle(surf, stripe, rect.center, max(1, stripe_w // 2))
    if c in board.head_cells:
        pygame.draw.circle(surf, head, rect.center, max(2, pipe_w // 2 + max(1, size // 20)))


def _draw_trail(surface: pygame.Surface, board, c: Cell, rect: pygame.Rect) -> None:
    trail_w = max(1, round(rect.w * TRAIL_WIDTH))
    states = []
    for d in DELTAS:
        state = board.trail.get(edge_key(c, step(c, d)))
        if state is None:
            continue
        surface.fill(TRAIL_COLOR if state else TRAIL_DIM_COLOR, spoke(rect, d, trail_w))
        states.append(state)
    if states:
        color = TRAIL_COLOR if any(states) else TRAIL_DIM_COLOR
        pygame.draw.circle(surface, color, rect.center, max(1, trail_w // 2))


def _draw_markers(surface: pygame.Surface, board, c: Cell, rect: pygame.Rect,
                  draw_dot: bool) -> None:
    radius = max(2, round(rect.w * MARKER_RADIUS))
    if c == board.end:
        pygame.draw.circle(surface, END_COLOR, rect.center, radius)
    if c == board.start:
        if board.dot is None or board.dot == board.start:
            pygame.draw.circle(surface, START_COLOR, rect.center, radius)
        else:
            pygame.draw.circle(surface, START_COLOR, rect.center, radius, max(1, radius // 3))
    if draw_dot and c == board.dot and c != board.start:
        dot_radius = max(1, round(radius * DOT_AT_END_SCALE)) if c == board.end else radius
        pygame.draw.circle(surface, START_COLOR, rect.center, dot_radius)


class BoardRenderer:
    def __init__(self, surface: pygame.Surface):
        self.surface = surface
        self._palettes: dict[float, tuple] = {}

    def apply(self, board: Board, changes: Changes) -> list[pygame.Rect]:
        rects = []
        if changes.clear:
            self.surface.fill(BLACK)
            rects.append(self.surface.get_rect())
            self._palettes.clear()
        if board.geometry is not None:
            for c in changes.cells:
                rects.append(self._draw_cell(board, c))
        return rects

    def _draw_cell(self, board: Board, c: Cell) -> pygame.Rect:
        rect = pygame.Rect(board.geometry.cell_rect(c))
        draw_cell(self.surface, board, c, rect, self._palettes)
        return rect
