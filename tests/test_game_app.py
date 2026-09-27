import pygame
import pytest

from maze_saver.maze import E, N, S, W, step
from maze_game import benchmark, config
from maze_game.__main__ import _valid_key
from maze_game.app import Game, nav_for
from maze_game.config import GameSettings
from maze_game.keymap import Keymap
from maze_game.round import SINGLE_HUE, Phase
from maze_game.ui.custom_dialog import CustomDialog
from maze_game.ui.settings_panel import SettingsPanel

KEY_FOR_DIR = {N: pygame.K_w, E: pygame.K_d, S: pygame.K_s, W: pygame.K_a}


@pytest.fixture
def game(tmp_path):
    pygame.init()
    g = Game(GameSettings(animated=False, glide_speed=40, solve_speed=500), Keymap(),
             tmp_path / "config.json")
    yield g
    pygame.quit()


def frames(game, n, dt=1 / 60):
    for _ in range(n):
        game.frame(dt)


def press(game, key):
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))


def release(game, key):
    game.handle(pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode="", scancode=0))


def until_play(game):
    for _ in range(2000):
        if game.round.phase is Phase.PLAY:
            return
        game.frame(1 / 60)
    raise AssertionError("maze never finished growing")


def test_nav_for():
    k = Keymap()
    assert nav_for("w", k) == "up"
    assert nav_for("return", k) == "confirm"
    assert nav_for("space", k) == "confirm"
    assert nav_for("escape", k) == "cancel"
    assert nav_for("7", k) == "digit:7"
    assert nav_for("[7]", k) == "digit:7"
    assert nav_for("x", k) is None


def test_valid_key():
    pygame.init()
    try:
        assert _valid_key("w") and _valid_key("[+]") and not _valid_key("nope")
    finally:
        pygame.quit()


def test_new_game_grows_then_plays(game):
    until_play(game)


def test_space_skips_growth(tmp_path):
    pygame.init()
    try:
        g = Game(GameSettings(gen_speed=5), Keymap(), tmp_path / "config.json")
        g.frame(1 / 60)
        assert g.round.phase is Phase.GROW
        press(g, pygame.K_SPACE)
        until_play(g)
    finally:
        pygame.quit()


def test_keyboard_moves_the_dot(game):
    until_play(game)
    r = game.round
    d = next(d for d in (N, E, S, W) if r.grid.open_dirs(r.start) & d)
    press(game, KEY_FOR_DIR[d])
    frames(game, 10)
    release(game, KEY_FOR_DIR[d])
    frames(game, 10)
    assert r.steps >= 1 and not r.mover.moving


def test_dash_click_moves_one_straight_run(game):
    until_play(game)
    r = game.round
    n = next(step(r.start, d) for d in (N, E, S, W) if r.grid.open_dirs(r.start) & d)
    x, y, w, h = game.camera.cell_rect(n)
    pr = game.play_rect
    pos = (pr.x + x + w // 2, pr.y + y + h // 2)
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
    frames(game, 30)
    assert r.path.route[:2] == [r.start, n]


def test_autosolve_wins_then_replay_resets(game):
    until_play(game)
    game.do("autosolve")
    for _ in range(20000):
        if game.round.phase is Phase.WON:
            break
        game.frame(1 / 60)
    r = game.round
    assert r.phase is Phase.WON and r.assisted and r.auto_steps > 0 and r.steps == 0
    frames(game, 70)
    assert r.win_overlay_visible
    game.do("replay")
    assert r.phase is Phase.PLAY and r.auto_steps == 0 and game.auto is None


def test_movement_key_interrupts_autosolve(game):
    until_play(game)
    game.do("autosolve")
    frames(game, 2)
    press(game, pygame.K_d)
    assert game.auto is None
    release(game, pygame.K_d)


def test_number_key_sets_difficulty_and_saves(game, tmp_path):
    press(game, pygame.K_3)
    assert game.settings.difficulty == "large"
    assert config.load(tmp_path / "config.json")[0].difficulty == "large"


def test_escape_opens_and_closes_settings(game):
    press(game, pygame.K_ESCAPE)
    assert isinstance(game.dialog, SettingsPanel)
    press(game, pygame.K_ESCAPE)
    assert game.dialog is None


def test_settings_apply_saves(game, tmp_path):
    press(game, pygame.K_ESCAPE)
    press(game, pygame.K_d)  # Follow bends -> Off
    press(game, pygame.K_UP)  # wraps to Cancel
    press(game, pygame.K_UP)  # Apply
    press(game, pygame.K_RETURN)
    assert game.dialog is None and game.settings.follow_bends is False
    assert config.load(tmp_path / "config.json")[0].follow_bends is False


def test_custom_dialog_starts_a_custom_maze(game):
    press(game, pygame.K_5)
    assert isinstance(game.dialog, CustomDialog)
    press(game, pygame.K_RETURN)
    assert game.dialog is None and game.settings.difficulty == "custom"


def test_colors_toggle(game):
    game.do("colors")
    assert game.settings.multicolor is False
    assert set(game.round.hues) == {SINGLE_HUE}


def test_zoom_and_reset(game):
    until_play(game)
    game.do("zoom_in")
    assert game.camera.zoomed
    game.do("zoom_reset")
    assert not game.camera.zoomed


def test_timer_pauses_while_a_dialog_is_open(game):
    until_play(game)
    game.do("autosolve")
    frames(game, 5)
    assert game.round.elapsed > 0
    assert game.round.phase is Phase.PLAY
    game.do("settings")
    before = game.round.elapsed
    frames(game, 30)
    assert game.round.elapsed == before


def test_focus_lost_clears_press_and_dragging(game):
    until_play(game)
    r = game.round
    n = next(step(r.start, d) for d in (N, E, S, W) if r.grid.open_dirs(r.start) & d)
    x, y, w, h = game.camera.cell_rect(n)
    pr = game.play_rect
    pos = (pr.x + x + w // 2, pr.y + y + h // 2)
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
    game.dragging = True
    game.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    assert game.press is None
    assert game.dragging is False


def test_minimized_pauses_movement(game):
    until_play(game)
    game.do("autosolve")
    frames(game, 3)
    r = game.round
    game.minimized = True
    steps_before, auto_steps_before = r.steps, r.auto_steps
    frames(game, 30)
    assert r.steps == steps_before
    assert r.auto_steps == auto_steps_before


def test_bench_scene_returns_frames_and_a_build_rate(game, monkeypatch):
    monkeypatch.setattr(benchmark, "FINISH_SECONDS", 0.05)
    monkeypatch.setattr(benchmark, "RUN_SECONDS", 0.05)
    times, rate = game._bench_scene(12, 1)
    assert times and all(t > 0 for t in times) and 0 < rate < 1


def test_run_benchmark_saves_the_result(game, monkeypatch, tmp_path):
    monkeypatch.setattr(game, "_bench_scene",
                        lambda n, i: ([1 / 100] * 20, 1e-6) if n <= 200 else ([1 / 30] * 20, 1e-6))
    size = game.run_benchmark()
    pr = game.play_rect
    assert 196 <= size <= 200
    assert game.settings.bench_resolution == (pr.w, pr.h) and game.settings.bench_rate == 1e-6
    assert config.load(tmp_path / "config.json")[0].bench_size == size


def test_escape_cancels_the_benchmark(game):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="",
                                         scancode=0))
    assert game.run_benchmark() is None and game.settings.bench_size is None


def test_benchmark_from_the_custom_dialog_updates_it(game, monkeypatch):
    monkeypatch.setattr(game, "_bench_scene", lambda n, i: ([1 / 100] * 20, 1e-6))
    press(game, pygame.K_5)
    game._dialog_outcome("benchmark")
    assert game.dialog.bench_size == game.settings.bench_size is not None
    assert game.dialog.bench_rate == 1e-6
