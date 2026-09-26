import random

import pygame
import pytest

from maze_saver.board import Board, Phase
from maze_saver.config import Settings
from maze_saver.maze import DELTAS, E, N, S, W, step
from maze_saver.render import END_COLOR, START_COLOR, TRAIL_COLOR, TRAIL_DIM_COLOR, BoardRenderer

FAST = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500, hold_seconds=0.5)
DT = 1 / 60


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def run_until(board, renderer, phase):
    rects = []
    for _ in range(100000):
        rects += renderer.apply(board, board.update(DT))
        if board.phase is phase:
            return rects
    raise AssertionError(f"never reached {phase}")


def center(board, c):
    x, y, s, _ = board.geometry.cell_rect(c)
    return (x + s // 2, y + s // 2)


def edge_point(board, c, d):
    x, y, s, _ = board.geometry.cell_rect(c)
    cx, cy = x + s // 2, y + s // 2
    return {N: (cx, y), S: (cx, y + s - 1), W: (x, cy), E: (x + s - 1, cy)}[d]


def rgb(surface, point):
    return tuple(surface.get_at(point))[:3]


def test_clear_fills_black_and_reports_whole_surface():
    surface = pygame.Surface((400, 300))
    surface.fill((9, 9, 9))
    board = Board(400, 300, FAST, random.Random(1))
    rects = BoardRenderer(surface).apply(board, board.update(0.01))
    assert rects == [surface.get_rect()]
    assert rgb(surface, (5, 5)) == (0, 0, 0)


def test_dots_drawn_at_start_and_end():
    surface = pygame.Surface((400, 300))
    board = Board(400, 300, FAST, random.Random(2))
    run_until(board, BoardRenderer(surface), Phase.DOTS)
    assert rgb(surface, center(board, board.start)) == START_COLOR
    assert rgb(surface, center(board, board.end)) == END_COLOR


def test_pipes_reach_the_edge_only_where_open():
    surface = pygame.Surface((400, 300))
    board = Board(400, 300, FAST, random.Random(3))
    run_until(board, BoardRenderer(surface), Phase.SOLVE)
    for c in board.grid.cells():
        bits = board.grid.open_dirs(c)
        for d in DELTAS:
            color = rgb(surface, edge_point(board, c, d))
            if bits & d:
                assert color != (0, 0, 0), (c, d)
            else:
                assert color == (0, 0, 0), (c, d)


def test_trail_colors_after_solve():
    surface = pygame.Surface((400, 300))
    board = Board(400, 300, FAST, random.Random(4))
    run_until(board, BoardRenderer(surface), Phase.HOLD)
    for (a, b), bright in board.trail.items():
        d = next(d for d in DELTAS if step(a, d) == b)
        expected = TRAIL_COLOR if bright else TRAIL_DIM_COLOR
        assert rgb(surface, edge_point(board, a, d)) == expected


def test_rects_stay_inside_surface():
    surface = pygame.Surface((400, 300))
    board = Board(400, 300, FAST, random.Random(5))
    renderer = BoardRenderer(surface)
    rects = run_until(board, renderer, Phase.HOLD)
    rects += renderer.apply(board, board.update(FAST.hold_seconds + 0.01))
    assert rects
    assert all(surface.get_rect().contains(r) for r in rects)
