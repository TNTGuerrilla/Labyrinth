import random
from types import SimpleNamespace

import pygame
import pytest

from maze_saver.board import Board, Phase
from maze_saver.config import Settings
from maze_saver.maze import DELTAS, E, N, S, W, Cell, Grid, step
from maze_saver.render import END_COLOR, START_COLOR, TRAIL_COLOR, TRAIL_DIM_COLOR, BoardRenderer, draw_cell

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


def fake_board(grid, **kw):
    attrs = dict(grid=grid, region_of={}, hues=[0.3], welds={}, trail={}, head_cells=set(),
                 start=None, end=None, dot=None)
    attrs.update(kw)
    return SimpleNamespace(**attrs)


def test_draw_cell_draws_pipe_into_given_rect():
    surface = pygame.Surface((40, 40))
    grid = Grid(2, 1)
    grid.carve((0, 0), (1, 0))
    board = fake_board(grid, region_of={(0, 0): 0, (1, 0): 0})
    draw_cell(surface, board, (0, 0), pygame.Rect(0, 0, 20, 20), {})
    assert rgb(surface, (19, 10)) != (0, 0, 0)  # east side is open
    assert rgb(surface, (10, 0)) == (0, 0, 0)  # north side is closed
    assert rgb(surface, (30, 10)) == (0, 0, 0)  # nothing drawn outside the rect


def test_draw_cell_can_skip_the_dot():
    grid = Grid(3, 1)
    board = fake_board(grid, start=(1, 0), end=(2, 0), dot=(0, 0))
    surface = pygame.Surface((20, 20))
    draw_cell(surface, board, (0, 0), pygame.Rect(0, 0, 20, 20), {})
    assert rgb(surface, (10, 10)) == START_COLOR
    draw_cell(surface, board, (0, 0), pygame.Rect(0, 0, 20, 20), {}, draw_dot=False)
    assert rgb(surface, (10, 10)) == (0, 0, 0)


def test_underlay_runs_under_the_pipe():
    RED = (255, 0, 0)

    def fill_red(surface, rect):
        surface.fill(RED, rect)

    grid = Grid(2, 1)
    grid.carve((0, 0), (1, 0))
    board = fake_board(grid, region_of={(0, 0): 0, (1, 0): 0})
    surface = pygame.Surface((40, 40))
    draw_cell(surface, board, (0, 0), pygame.Rect(0, 0, 20, 20), {}, underlay=fill_red)
    assert rgb(surface, (19, 10)) != RED  # east spoke: pipe drawn on top
    assert rgb(surface, (0, 0)) == RED  # corner: untouched by the pipe
