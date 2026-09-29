import itertools
from dataclasses import replace

import pygame
import pytest

from maze_game import game_render
from maze_game.assist import route
from maze_game.camera import Camera
from maze_game.game_render import GameRenderer
from maze_game.steering import PathSteer
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


def make_scene(board, clock=None):
    camera = Camera(board.grid.cols, board.grid.rows, PLAY.w, PLAY.h)
    renderer = GameRenderer(PLAY.size, clock=clock) if clock else GameRenderer(PLAY.size)
    return camera, renderer, pygame.Surface((400, 340))


def test_first_render_draws_the_maze_and_the_dot():
    r = grown()
    camera, renderer, screen = make_scene(r)
    renderer.render(screen, PLAY, r, camera, set())
    assert not renderer.pending
    x, y, w, h = camera.cell_rect(r.start)
    assert tuple(screen.get_at((x + w // 2, PLAY.y + y + h // 2)))[:3] == START_COLOR


def test_budget_spreads_a_big_redraw_over_frames():
    r = big_round()
    camera, renderer, screen = make_scene(r, fake_clock())
    frames = 0
    while True:
        renderer.render(screen, PLAY, r, camera, set())
        frames += 1
        if not renderer.pending:
            break
    assert frames > 2


def test_changed_cells_are_drawn_before_the_sweep(monkeypatch):
    r = big_round()
    camera, renderer, screen = make_scene(r, fake_clock())
    calls = []
    real = game_render.draw_cell
    monkeypatch.setattr(game_render, "draw_cell",
                        lambda *a, **k: (calls.append(a[2]), real(*a, **k)))
    renderer.render(screen, PLAY, r, camera, {(79, 59)})
    assert calls[0] == (79, 59)


def test_scrolling_redraws_only_the_exposed_strip(monkeypatch):
    r = big_round()
    camera, renderer, screen = make_scene(r)
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
    camera, renderer, screen = make_scene(r, fake_clock())
    settle(renderer, screen, PLAY, r, camera)
    camera.zoom_by(1, (40, 30))
    renderer.render(screen, PLAY, r, camera, set())
    assert renderer.pending
    assert pygame.transform.average_color(renderer.layer)[:3] != (0, 0, 0)


def test_low_detail_when_cells_are_tiny():
    r = grown(300, 200, replace(FAST, animated=False))
    camera, renderer, screen = make_scene(r)
    assert camera.cell_px < game_render.LOW_DETAIL_PX
    settle(renderer, screen, PLAY, r, camera)
    assert pygame.transform.average_color(renderer.layer)[:3] != (0, 0, 0)


def test_grid_lines_on_cell_corners():
    r = grown()
    camera, renderer, screen = make_scene(r)
    settle(renderer, screen, PLAY, r, camera)
    x, y, w, h = camera.cell_rect((0, 0))
    assert w >= game_render.GRID_MIN_PX
    assert tuple(screen.get_at((x, PLAY.y + y)))[:3] == game_render.grid_color(20)

    renderer.show_grid = False
    renderer.invalidate()
    settle(renderer, screen, PLAY, r, camera)
    assert tuple(screen.get_at((x, PLAY.y + y)))[:3] == (0, 0, 0)


def test_grid_color_scales_with_strength():
    assert game_render.grid_color(20) == (30, 32, 40)
    assert game_render.grid_color(10) == (15, 16, 20)
    assert game_render.grid_color(100) == (150, 160, 200)
    assert game_render.grid_color(35) == (52, 56, 70)


def test_grid_lines_use_the_strength():
    r = grown()
    camera, renderer, screen = make_scene(r)
    renderer.grid_strength = 100
    renderer.invalidate()
    settle(renderer, screen, PLAY, r, camera)
    x, y, w, h = camera.cell_rect((0, 0))
    assert tuple(screen.get_at((x, PLAY.y + y)))[:3] == (150, 160, 200)


def test_no_grid_on_tiny_cells():
    r = grown(300, 200, replace(FAST, animated=False))
    camera, renderer, screen = make_scene(r)
    assert camera.cell_px < game_render.LOW_DETAIL_PX
    settle(renderer, screen, PLAY, r, camera)
    x, y, w, h = camera.cell_rect((0, 0))
    assert tuple(screen.get_at((x, PLAY.y + y)))[:3] != game_render.grid_color(20)


def test_overlays_never_touch_the_layer():
    r = grown()
    camera, renderer, screen = make_scene(r)
    settle(renderer, screen, PLAY, r, camera)
    before = pygame.image.tobytes(renderer.layer, "RGB")
    r.hint(5)
    r.flash()
    renderer.render(screen, PLAY, r, camera, set())
    assert pygame.image.tobytes(renderer.layer, "RGB") == before


def test_flash_arrow_when_the_finish_is_off_screen():
    r = big_round()
    camera, renderer, screen = make_scene(r)
    camera.zoom_by(100, (r.start[0] + 0.5, r.start[1] + 0.5))
    r.flash()
    settle(renderer, screen, PLAY, r, camera)


def test_resize_keeps_drawing():
    r = grown()
    camera, renderer, screen = make_scene(r)
    settle(renderer, screen, PLAY, r, camera)
    renderer.resize((500, 400))
    camera.resize(500, 400)
    bigger = pygame.Rect(0, 40, 500, 400)
    settle(renderer, pygame.Surface((500, 440)), bigger, r, camera)
    assert renderer.layer.get_size() == (500, 400)


def test_two_resizes_before_a_render_keep_the_stretch_preview():
    r = big_round()
    camera, renderer, screen = make_scene(r, fake_clock())
    settle(renderer, screen, PLAY, r, camera)
    camera.resize(500, 400)
    renderer.resize((500, 400))
    camera.resize(600, 450)
    renderer.resize((600, 450))
    bigger = pygame.Rect(0, 0, 600, 450)
    renderer.render(pygame.Surface((600, 450)), bigger, r, camera, set())
    assert pygame.transform.average_color(renderer.layer)[:3] != (0, 0, 0)


def test_win_pulse_skips_cells_outside_the_play_rect(monkeypatch):
    r = grown()
    camera, renderer, screen = make_scene(r)
    r.move(1000.0, PathSteer(route(r.grid, r.start, r.end)[1:]).choose)
    assert r.win_pulse_active
    camera.zoom_by(100, (r.end[0] + 0.5, r.end[1] + 0.5))
    calls = []
    real = pygame.draw.circle

    def fake_circle(surface, color, pos, *a, **k):
        calls.append(pos)
        return real(surface, color, pos, *a, **k)

    monkeypatch.setattr(pygame.draw, "circle", fake_circle)
    game_render.draw_overlays(screen, PLAY, r, camera)
    assert calls
    for pos in calls:
        assert PLAY.collidepoint(pos)


def test_changed_cells_are_drawn_before_scroll_strips(monkeypatch):
    r = big_round()
    camera, renderer, screen = make_scene(r, fake_clock())
    camera.zoom_by(3, (40, 30))
    settle(renderer, screen, PLAY, r, camera)
    calls = []
    real = game_render.draw_cell
    monkeypatch.setattr(game_render, "draw_cell",
                        lambda *a, **k: (calls.append(a[2]), real(*a, **k)))
    camera.cx += 1.0
    renderer.render(screen, PLAY, r, camera, {(40, 30)})
    assert calls[0] == (40, 30)
