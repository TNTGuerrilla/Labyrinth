import random
from dataclasses import replace

import pygame
import pytest

from maze_saver.maze import E, N, S, W, Grid, direction, step
from maze_game import benchmark, config
from maze_game.__main__ import _valid_key
from maze_game.app import Game, nav_for
from maze_game.config import GameSettings
from maze_game.keymap import Keymap
from maze_game.round import SINGLE_HUE, Phase
from maze_game.steering import KeyboardSteer
from maze_game.trail import Trail
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


def test_reverse_clears_the_turn_request(game):
    until_play(game)
    r = game.round
    d = next(d for d in (N, E, S, W) if r.grid.open_dirs(r.start) & d)
    press(game, KEY_FOR_DIR[d])
    game.frame(0.02)
    mover = r.mover
    assert mover.to is not None  # mid-segment, before any bend or fork can be reached
    opposite = direction(mover.to, mover.frm)
    press(game, KEY_FOR_DIR[opposite])
    assert game.keys.request is None
    assert mover.to is not None


def test_leftover_press_during_grow_is_dropped_before_play_begins(tmp_path):
    """A direction tapped (pressed and released) while the maze is still growing must
    not move the dot once PLAY begins, even though the tap is buffered as a request.
    Two mazes built from the same seed are identical, so the first one is used only
    to learn which direction will be open at the start, and the second reproduces
    the real bug scenario: the tap happens during GROW, before that is known."""
    pygame.init()
    try:
        settings = GameSettings(gen_speed=5)
        keymap = Keymap()
        probe = Game(settings, keymap, tmp_path / "probe.json")
        probe.rng = random.Random(3)
        probe.new_round()
        press(probe, pygame.K_SPACE)
        until_play(probe)
        d = next(dd for dd in (N, E, S, W) if probe.round.grid.open_dirs(probe.round.start) & dd)

        g = Game(settings, keymap, tmp_path / "config.json")
        g.rng = random.Random(3)
        g.new_round()
        assert g.round.phase is Phase.GROW
        press(g, KEY_FOR_DIR[d])
        release(g, KEY_FOR_DIR[d])
        press(g, pygame.K_SPACE)
        until_play(g)
        frames(g, 30)
        assert g.round.steps == 0
        assert g.round.timer_running is False
    finally:
        pygame.quit()


def test_leftover_press_on_the_win_screen_is_dropped_by_replay(game):
    until_play(game)
    r = game.round
    d = next(d for d in (N, E, S, W) if r.grid.open_dirs(r.start) & d)
    game.do("autosolve")
    for _ in range(20000):
        if r.phase is Phase.WON:
            break
        game.frame(1 / 60)
    frames(game, 70)
    assert r.win_overlay_visible
    press(game, KEY_FOR_DIR[d])
    release(game, KEY_FOR_DIR[d])
    game.do("replay")
    frames(game, 30)
    assert r.steps == 0
    assert r.timer_running is False


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


def test_mouse_press_and_dash_forget_keyboard_steering_position(game):
    until_play(game)
    r = game.round
    n = next(step(r.start, d) for d in (N, E, S, W) if r.grid.open_dirs(r.start) & d)
    x, y, w, h = game.camera.cell_rect(n)
    pr = game.play_rect
    pos = (pr.x + x + w // 2, pr.y + y + h // 2)

    def leave_stale_state():
        game.keys._stopped = True
        game.keys._pause_cell = r.mover.cell
        game.keys._last_cell = r.mover.cell

    leave_stale_state()
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))
    assert game.keys._stopped is False  # press/drag start forgets the stale position
    assert game.keys._pause_cell is None
    assert game.keys._last_cell is None

    leave_stale_state()
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos))
    assert game.keys._stopped is False  # the dash that follows the click forgets it again
    assert game.keys._pause_cell is None
    assert game.keys._last_cell is None


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


def test_autosolve_forgets_keyboard_steering_position(game):
    until_play(game)
    r = game.round
    game.keys._stopped = True
    game.keys._pause_cell = r.mover.cell
    game.keys._last_cell = r.mover.cell
    game.do("autosolve")
    assert game.keys._stopped is False
    assert game.keys._pause_cell is None
    assert game.keys._last_cell is None


def test_turn_pause_setting_reaches_the_keyboard_chooser(game):
    """Round.settings.turn_pause must reach the chooser _driver() builds for the
    keyboard, using a fork grid injected into the round for a deterministic check."""
    until_play(game)
    r = game.round
    cross = Grid(3, 3)
    for a, b in (((0, 1), (1, 1)), ((1, 1), (2, 1)), ((1, 1), (1, 0)), ((1, 1), (1, 2))):
        cross.carve(a, b)
    r.grid = cross
    r.start, r.end = (0, 1), (9, 9)

    game.keys = KeyboardSteer()
    game.keys.press(E)
    game.keys.request = None
    choose, _, _ = game._driver()
    assert choose((1, 1), (0, 1)) is None  # default turn_pause: waits at the fork

    game.settings = replace(game.settings, turn_pause=0.0)
    game.keys = KeyboardSteer()
    game.keys.press(E)
    game.keys.request = None
    choose, _, _ = game._driver()
    assert choose((1, 1), (0, 1)) == (2, 1)  # turn_pause=0: no pause needed


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


def test_show_grid_setting_reaches_the_renderer(tmp_path):
    pygame.init()
    g = Game(GameSettings(show_grid=False, animated=False, glide_speed=40, solve_speed=500),
             Keymap(), tmp_path / "config.json")
    try:
        assert g.renderer.show_grid is False
        g.do("settings")
        g.dialog.model.draft = replace(g.dialog.model.draft, show_grid=True)
        g._dialog_outcome("apply")
        assert g.renderer.show_grid is True
    finally:
        pygame.quit()


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
    game.handle(pygame.event.Event(pygame.WINDOWMINIMIZED))
    assert r.phase is Phase.PLAY and game.auto is not None
    steps_before, auto_steps_before = r.steps, r.auto_steps
    frames(game, 30)
    assert r.steps == steps_before
    assert r.auto_steps == auto_steps_before
    game.handle(pygame.event.Event(pygame.WINDOWMAXIMIZED))
    frames(game, 30)
    assert r.steps > steps_before or r.auto_steps > auto_steps_before


class _FakeAuto:
    """Mimics AutoSteer: `done` only flips once choose() is asked again after the last
    cell, exactly like the real solver only reports Solved on the next call."""

    def __init__(self, cells):
        self._cells = list(cells)
        self.done = False

    def choose(self, cell, came_from=None):
        if not self._cells:
            self.done = True
            return None
        return self._cells.pop(0)


def test_auto_solve_clears_when_the_round_is_won(game):
    until_play(game)
    r = game.round
    adj = next(step(r.end, d) for d in (N, E, S, W) if r.grid.open_dirs(r.end) & d)
    r.mover.place(adj)
    r.path = Trail(adj)
    game.settings = replace(game.settings, solve_speed=36)  # 0.6 cell per 1/60 s frame
    game.auto = _FakeAuto([r.end])
    game.frame(1 / 60)
    assert r.phase is Phase.WON
    assert game.auto is None
    assert game.dash is None


def test_replay_after_zoom_clears_the_stale_zoomed_margin(game):
    until_play(game)
    for _ in range(3):
        game.do("zoom_in")
    for _ in range(2000):
        game.frame(1 / 60)
        if not game.renderer.pending:
            break
    layer = game.renderer.layer
    w, h = layer.get_size()
    zoomed_pixels = [(x, y) for x in range(0, w, 20) for y in range(0, h, 20)
                     if layer.get_at((x, y))[:3] != (0, 0, 0)]
    assert zoomed_pixels
    game.do("replay")
    for _ in range(2000):
        game.frame(1 / 60)
        if not game.renderer.pending:
            break
    assert not game.camera.zoomed
    ox, oy = game.camera.origin()
    margin_pixels = [(x, y) for x, y in zoomed_pixels
                     if x < ox or y < oy or x >= w - ox or y >= h - oy]
    assert margin_pixels
    for x, y in margin_pixels:
        assert layer.get_at((x, y))[:3] == (0, 0, 0)


def test_toggle_fullscreen_does_not_resize_directly(game, monkeypatch):
    until_play(game)
    calls = []
    monkeypatch.setattr(game, "_resized", lambda: calls.append(1))
    game._toggle_fullscreen()
    assert calls == []
    game.handle(pygame.event.Event(pygame.WINDOWSIZECHANGED))
    assert calls == [1]


def test_benchmark_cancelled_by_a_resize_event(game):
    pygame.event.post(pygame.event.Event(pygame.WINDOWSIZECHANGED))
    assert game.run_benchmark() is None
    assert game.settings.bench_size is None


def test_nav_for_fixed_keys_win_over_rebound_movement_keys():
    k = Keymap()
    assert k.set_key("up", 0, "space")
    assert nav_for("space", k) == "confirm"
    assert "space" in k.keys_for("up")
    assert nav_for("up", k) == "up"


def test_save_ignores_oserror(game, monkeypatch):
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(config, "save", boom)
    game.do("colors")


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
