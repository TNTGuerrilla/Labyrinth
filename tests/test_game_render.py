import itertools
from dataclasses import replace

import pygame
import pytest

from maze_game import game_render
from maze_game.camera import Camera
from maze_game.game_render import GameRenderer
from maze_saver.render import START_COLOR
from tests.gameutil import FAST, grown

PLAY = pygame.Rect(0, 40, 400, 300)


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def fake_clock(step=0.001):
    ticks = itertools.count()
    return lambda: next(ticks) * step


def settle(renderer, screen, play, board, camera):
    for _ in range(10000):
        renderer.render(screen, play, board, camera, set())
        if not renderer.pending:
            return
    raise AssertionError("renderer never finished drawing")


def big_round():
    return grown(80, 60, replace(FAST, animated=False))


def setup(board, clock=None):
    camera = Camera(board.grid.cols, board.grid.rows, PLAY.w, PLAY.h)
    renderer = GameRenderer(PLAY.size, clock=clock) if clock else GameRenderer(PLAY.size)
    return camera, renderer, pygame.Surface((400, 340))


def test_first_render_draws_the_maze_and_the_dot():
    r = grown()
    camera, renderer, screen = setup(r)
    renderer.render(screen, PLAY, r, camera, set())
    assert not renderer.pending
    x, y, w, h = camera.cell_rect(r.start)
    assert tuple(screen.get_at((x + w // 2, PLAY.y + y + h // 2)))[:3] == START_COLOR


def test_budget_spreads_a_big_redraw_over_frames():
    r = big_round()
    camera, renderer, screen = setup(r, fake_clock())
    frames = 0
    while True:
        renderer.render(screen, PLAY, r, camera, set())
        frames += 1
        if not renderer.pending:
            break
    assert frames > 2


def test_changed_cells_are_drawn_before_the_sweep(monkeypatch):
    r = big_round()
    camera, renderer, screen = setup(r, fake_clock())
    calls = []
    real = game_render.draw_cell
    monkeypatch.setattr(game_render, "draw_cell",
                        lambda *a, **k: (calls.append(a[2]), real(*a, **k)))
    renderer.render(screen, PLAY, r, camera, {(79, 59)})
    assert calls[0] == (79, 59)


def test_scrolling_redraws_only_the_exposed_strip(monkeypatch):
    r = big_round()
    camera, renderer, screen = setup(r)
    camera.zoom_by(3, (40, 30))
    settle(renderer, screen, PLAY, r, camera)
    calls = []
    real = game_render.draw_cell
    monkeypatch.setattr(game_render, "draw_cell",
                        lambda *a, **k: (calls.append(a[2]), real(*a, **k)))
    camera.cx += 1.0
    renderer.render(screen, PLAY, r, camera, set())
    assert 0 < len(calls) < 200


def test_zoom_keeps_a_stretched_image_while_resweeping():
    r = big_round()
    camera, renderer, screen = setup(r, fake_clock())
    settle(renderer, screen, PLAY, r, camera)
    camera.zoom_by(1, (40, 30))
    renderer.render(screen, PLAY, r, camera, set())
    assert renderer.pending
    assert pygame.transform.average_color(renderer.layer)[:3] != (0, 0, 0)


def test_low_detail_when_cells_are_tiny():
    r = grown(300, 200, replace(FAST, animated=False))
    camera, renderer, screen = setup(r)
    assert camera.cell_px < game_render.LOW_DETAIL_PX
    settle(renderer, screen, PLAY, r, camera)
    assert pygame.transform.average_color(renderer.layer)[:3] != (0, 0, 0)


def test_overlays_never_touch_the_layer():
    r = grown()
    camera, renderer, screen = setup(r)
    settle(renderer, screen, PLAY, r, camera)
    before = pygame.image.tobytes(renderer.layer, "RGB")
    r.hint(5)
    r.flash()
    renderer.render(screen, PLAY, r, camera, set())
    assert pygame.image.tobytes(renderer.layer, "RGB") == before


def test_flash_arrow_when_the_finish_is_off_screen():
    r = big_round()
    camera, renderer, screen = setup(r)
    camera.zoom_by(100, (r.start[0] + 0.5, r.start[1] + 0.5))
    r.flash()
    settle(renderer, screen, PLAY, r, camera)


def test_resize_keeps_drawing():
    r = grown()
    camera, renderer, screen = setup(r)
    settle(renderer, screen, PLAY, r, camera)
    renderer.resize((500, 400))
    camera.resize(500, 400)
    bigger = pygame.Rect(0, 40, 500, 400)
    settle(renderer, pygame.Surface((500, 440)), bigger, r, camera)
    assert renderer.layer.get_size() == (500, 400)
