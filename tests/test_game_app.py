import itertools
import random
from dataclasses import replace

import pygame
import pytest

from maze_saver.maze import E, N, S, W, Grid, direction, step
from maze_game import benchmark, config
from maze_game.__main__ import _valid_key
from maze_game.app import BenchmarkCancelled, Game, nav_for
from maze_game.config import GameSettings
from maze_game.keymap import Keymap
from maze_game.round import SINGLE_HUE, Phase, Round
from maze_game.steering import KeyboardSteer
from maze_game.trail import Trail
from maze_game.ui.custom_dialog import CustomDialog
from maze_game.ui import toolbar as toolbar_module
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
    assert r.explored >= 1 and not r.mover.moving


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
        assert g.round.explored == 0
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
    assert r.explored == 0
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
    assert r.phase is Phase.WON and r.assisted and r.auto_explored > 0 and r.explored == 0
    frames(game, 70)
    assert r.win_overlay_visible
    game.do("replay")
    assert r.phase is Phase.PLAY and r.auto_explored == 0 and game.auto is None


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
    # A large maze: a small one at 100% coverage can already fill cells up to the zoom limit.
    game.new_round("large")
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
    explored_before, auto_before = r.explored, r.auto_explored
    frames(game, 30)
    assert r.explored == explored_before
    assert r.auto_explored == auto_before
    game.handle(pygame.event.Event(pygame.WINDOWMAXIMIZED))
    frames(game, 30)
    assert r.explored > explored_before or r.auto_explored > auto_before


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
    game.settings = replace(game.settings, coverage=80)  # 100% leaves no margin to check
    game.new_round()
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
    assert k.set_key("up", 0, "return")
    assert nav_for("return", k) == "confirm"
    assert "return" in k.keys_for("up")
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


def test_run_benchmark_saves_the_coverage_it_ran_at(game, monkeypatch):
    monkeypatch.setattr(game, "_bench_scene", lambda n, i: ([1 / 100] * 20, 1e-6))
    game.settings = replace(game.settings, coverage=75)
    game.run_benchmark()
    assert game.settings.bench_coverage == 75


def test_a_benchmark_at_another_coverage_is_not_recommended(game):
    pr = game.play_rect
    game.settings = replace(game.settings, bench_size=300, bench_rate=1e-6,
                            bench_resolution=(pr.w, pr.h), bench_coverage=100)
    assert game._bench_for_screen() == (300, 1e-6)
    game.settings = replace(game.settings, coverage=60)
    assert game._bench_for_screen() == (None, None)
    press(game, pygame.K_5)
    assert game.dialog.bench_size is None


def test_escape_cancels_the_benchmark_while_growth_finishes(game, monkeypatch):
    """After the rendered fast-forward, the rest of the growth still reads events."""
    monkeypatch.setattr(benchmark, "FINISH_SECONDS", 0.0)
    real = Round.finish_growth_now

    def finish(scene, on_chunk=None):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0,
                                             unicode="", scancode=0))
        assert on_chunk is not None
        on_chunk()
        real(scene, on_chunk)
    monkeypatch.setattr(Round, "finish_growth_now", finish)
    with pytest.raises(BenchmarkCancelled):
        game._bench_scene(40, 1)


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


def test_benchmark_from_settings_updates_the_draft_coverage(game, monkeypatch):
    monkeypatch.setattr(game, "_bench_scene", lambda n, i: ([1 / 100] * 20, 1e-6))
    game.settings = replace(game.settings, coverage=80)
    game._open_settings()
    game._dialog_outcome("benchmark")
    assert game.dialog.model.draft.bench_coverage == 80
    assert game.dialog.model.bench_text().startswith("Recommended max")


from labyrinth_update.releases import GAME_WINDOWS
from labyrinth_update.updater import Updater
from maze_game import app as game_app

UPDATE_LIST = [{"tag_name": "labyrinth-v9.0.0", "assets": [{
    "name": "Labyrinth.exe", "browser_download_url": "https://github.com/dl/Labyrinth.exe",
    "digest": "sha256:" + "ab" * 32}]}]


@pytest.fixture
def updated_game(tmp_path):
    pygame.init()
    u = Updater(GAME_WINDOWS, "1.0.0", tmp_path / "update.json", True,
                fetch=lambda: UPDATE_LIST, target=tmp_path / "Labyrinth.exe")
    u.check()
    u.wait(5)
    g = Game(GameSettings(animated=False), Keymap(), tmp_path / "config.json", updater=u)
    yield g
    pygame.quit()


def click(game, action):
    game.frame(1 / 60)
    pos = game.toolbar.hits.rect_for(action).center
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def test_toolbar_offers_the_update(updated_game):
    updated_game.frame(1 / 60)
    assert updated_game.toolbar.hits.rect_for("update") is not None


def test_no_updater_no_button(game):
    game.frame(1 / 60)
    assert game.toolbar.hits.rect_for("update") is None


def test_update_click_installs_then_restarts(updated_game, monkeypatch):
    installed, launched = [], []
    monkeypatch.setattr(game_app, "install_game",
                        lambda release, target, progress: installed.append((release.version, target)))
    monkeypatch.setattr(game_app, "relaunch", lambda target, args=(): launched.append(target))
    click(updated_game, "update")
    updated_game.updater.wait(5)
    updated_game.frame(1 / 60)
    assert installed == [("9.0.0", updated_game.updater.target)]
    assert launched == [updated_game.updater.target]
    assert not updated_game.running


def test_failed_update_shows_and_can_be_dismissed(updated_game, monkeypatch):
    from labyrinth_update.net import UpdateError

    def broken(release, target, progress):
        raise UpdateError("The download was interrupted.")

    monkeypatch.setattr(game_app, "install_game", broken)
    click(updated_game, "update")
    updated_game.updater.wait(5)
    updated_game.frame(1 / 60)
    assert updated_game.running
    assert updated_game.toolbar.hits.rect_for("update") is not None
    click(updated_game, "update_dismiss")
    updated_game.frame(1 / 60)
    assert updated_game.toolbar.hits.rect_for("update") is None


def test_dismiss_hides_the_button(updated_game):
    click(updated_game, "update_dismiss")
    updated_game.frame(1 / 60)
    assert updated_game.toolbar.hits.rect_for("update") is None


def test_turning_checks_off_in_settings_hides_the_button(updated_game):
    updated_game.do("settings")
    panel = updated_game.dialog
    panel.model.draft = replace(panel.model.draft, check_updates=False)
    updated_game._dialog_outcome("apply")
    updated_game.frame(1 / 60)
    assert updated_game.toolbar.hits.rect_for("update") is None


def test_opening_settings_checks_for_updates(tmp_path):
    pygame.init()
    try:
        # Create a counting fetch function
        fetch_count = [0]
        def counting_fetch():
            fetch_count[0] += 1
            return UPDATE_LIST

        # Use a fixed clock so the weekly check is not due
        fixed_clock = lambda: 1000.0

        # Create updater with counting fetch and fixed clock
        u = Updater(GAME_WINDOWS, "1.0.0", tmp_path / "update.json", True,
                    fetch=counting_fetch, clock=fixed_clock,
                    target=tmp_path / "Labyrinth.exe")

        # Create game with the updater
        g = Game(GameSettings(animated=False), Keymap(), tmp_path / "config.json", updater=u)

        # Initially, no fetch has happened (check not due without force)
        assert fetch_count[0] == 0

        # Opening settings should trigger a check
        g.do("settings")
        u.wait(5)
        g.frame(1 / 60)

        # Fetch should have been called once
        assert fetch_count[0] == 1

        # Close the dialog
        g._close_dialog()

        # Now test with disabled updater
        g.updater.set_enabled(False)
        fetch_count[0] = 0

        # Opening settings with disabled updater should not fetch
        g.do("settings")
        u.wait(5)
        g.frame(1 / 60)

        # Fetch should not have been called
        assert fetch_count[0] == 0
    finally:
        pygame.quit()


import json  # noqa: E402

from labyrinth_update.notes import NoteEntry  # noqa: E402
from labyrinth_update.state import UpdateState, save as save_state  # noqa: E402
from maze_game.ui.whats_new_dialog import WhatsNewDialog  # noqa: E402


def game_after_update(tmp_path, notes="- Faster mazes"):
    save_state(tmp_path / "update.json",
               UpdateState(last_run_version="0.9.0", notes=(NoteEntry("1.0.0", notes),)))
    u = Updater(GAME_WINDOWS, "1.0.0", tmp_path / "update.json", True, fetch=lambda: [],
                target=tmp_path / "Labyrinth.exe")
    return Game(GameSettings(animated=False), Keymap(), tmp_path / "config.json", updater=u)


def test_first_run_after_an_update_shows_whats_new_once(tmp_path):
    pygame.init()
    try:
        g = game_after_update(tmp_path)
        assert isinstance(g.dialog, WhatsNewDialog)
        assert g.dialog.title == "Labyrinth updated to 1.0.0"
        g.frame(1 / 60)
        press(g, pygame.K_RETURN)
        assert g.dialog is None
        data = json.loads((tmp_path / "update.json").read_text(encoding="utf-8"))
        assert data["last_run_version"] == "1.0.0"
        assert game_after_update_again(tmp_path).dialog is None
    finally:
        pygame.quit()


def game_after_update_again(tmp_path):
    u = Updater(GAME_WINDOWS, "1.0.0", tmp_path / "update.json", True, fetch=lambda: [],
                target=tmp_path / "Labyrinth.exe")
    return Game(GameSettings(animated=False), Keymap(), tmp_path / "config.json", updater=u)


def test_whats_new_scrolls_with_arrows_and_the_wheel(tmp_path):
    pygame.init()
    try:
        g = game_after_update(tmp_path, "\n".join(f"- line {i}" for i in range(80)))
        g.frame(1 / 60)
        press(g, pygame.K_DOWN)
        assert g.dialog.scroll == 1
        g.handle(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
        assert g.dialog.scroll == 4
        press(g, pygame.K_ESCAPE)
        assert g.dialog is None
    finally:
        pygame.quit()


def test_info_links_open_the_browser(game, monkeypatch):
    opened = []
    monkeypatch.setattr(game_app, "open_browser", opened.append)
    game.do("settings")
    game._dialog_outcome("github")
    game._dialog_outcome("license")
    assert opened == ["https://github.com/TNTGuerrilla/Labyrinth",
                      "https://github.com/TNTGuerrilla/Labyrinth/blob/master/LICENSE"]


def test_info_from_source_has_no_update_controls(game):
    game.do("settings")
    game.frame(1 / 60)
    assert game.dialog.model.info.updates is False


def test_check_now_from_info_reports_the_result(updated_game):
    updated_game.do("settings")
    updated_game.updater.wait(5)
    updated_game.updater.dismiss()
    updated_game._dialog_outcome("check_now")
    updated_game.updater.wait(5)
    updated_game.frame(1 / 60)
    info = updated_game.dialog.model.info
    assert info.status == "Version 9.0.0 is available" and info.can_update


def test_whats_new_from_info_returns_to_settings(updated_game):
    updated_game.do("settings")
    panel = updated_game.dialog
    updated_game._dialog_outcome("whats_new")
    assert isinstance(updated_game.dialog, WhatsNewDialog)
    assert updated_game.dialog.title == "Labyrinth updated to 1.0.0"
    press(updated_game, pygame.K_ESCAPE)
    assert updated_game.dialog is panel


def test_space_starts_the_next_maze_from_the_win_panel(game):
    until_play(game)
    game.do("autosolve")
    for _ in range(3000):
        game.frame(1 / 60)
        if game.round.win_overlay_visible:
            break
    first = game.round
    press(game, pygame.K_SPACE)
    assert game.round is not first


def test_space_still_works_when_hint_is_bound_elsewhere(tmp_path):
    pygame.init()
    keys = Keymap()
    keys.set_key("hint", 0, "h")
    g = Game(GameSettings(), keys, tmp_path / "config.json")
    press(g, pygame.K_SPACE)
    assert g.round.fast_forward
    pygame.quit()


@pytest.fixture
def saver(tmp_path):
    pygame.init()
    g = Game(GameSettings(animated=False, screensaver_speed=500, screensaver_pause=0.5),
             Keymap(), tmp_path / "config.json")
    yield g
    pygame.quit()


def saver_state(game, monkeypatch):
    """The ToolbarState of the next drawn frame."""
    seen = []
    real = game.toolbar.draw
    monkeypatch.setattr(game.toolbar, "draw",
                        lambda surface, keymap, state, mouse: (seen.append(state),
                                                               real(surface, keymap, state, mouse)))
    game.frame(1 / 60)
    return seen[-1]


def test_m_starts_the_screensaver_with_a_new_maze(saver):
    first = saver.round
    press(saver, pygame.K_m)
    assert saver.screensaver and saver.round is not first


def test_screensaver_solves_pauses_and_starts_the_next_maze(saver, monkeypatch):
    drawn = []
    monkeypatch.setattr(saver.win_screen, "draw", lambda *a: drawn.append(a))
    saver.start_screensaver()
    first = saver.round
    for _ in range(20000):
        saver.frame(1 / 60)
        if saver.round is not first:
            break
    assert first.phase is Phase.WON and saver.round is not first
    assert saver.screensaver and drawn == []  # no win panel in screensaver mode


def test_screensaver_pauses_on_the_solved_maze(saver):
    saver.start_screensaver()
    first = saver.round
    for _ in range(20000):
        saver.frame(1 / 60)
        if first.phase is Phase.WON:
            break
    for _ in range(int(0.4 * 60)):
        saver.frame(1 / 60)
    assert saver.round is first  # still inside the 0.5 s pause


@pytest.mark.parametrize("key", [pygame.K_SPACE, pygame.K_ESCAPE])
def test_space_or_escape_stops_it_without_skipping_or_opening_settings(tmp_path, key):
    pygame.init()
    g = Game(GameSettings(animated=True), Keymap(), tmp_path / "config.json")
    g.start_screensaver()
    running = g.round
    press(g, key)
    assert not g.screensaver and g.round is not running
    assert g.round.phase is Phase.GROW and not g.round.fast_forward  # growth not skipped
    assert g.dialog is None
    pygame.quit()


def test_other_input_does_not_stop_it(saver):
    saver.start_screensaver()
    running = saver.round
    zoom = saver.camera.zoom
    for key in (pygame.K_w, pygame.K_3, pygame.K_q, pygame.K_e, pygame.K_z):
        press(saver, key)
    centre = saver.play_rect.center
    saver.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=centre))
    saver.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=centre))
    saver.handle(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=1))
    saver.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=(5, 300), rel=(1, 1), buttons=(0, 0, 0)))
    saver.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    saver.handle(pygame.event.Event(pygame.WINDOWSIZECHANGED, x=1000, y=700))
    saver.handle(pygame.event.Event(pygame.WINDOWMINIMIZED))
    saver.handle(pygame.event.Event(pygame.WINDOWRESTORED))
    assert saver.screensaver and saver.round is running
    assert saver.settings.difficulty == GameSettings().difficulty
    assert saver.camera.zoom == zoom


def test_f11_toggles_fullscreen_and_keeps_it_running(saver, monkeypatch):
    calls = []
    monkeypatch.setattr(saver, "_toggle_fullscreen", lambda: calls.append(1))
    saver.start_screensaver()
    press(saver, pygame.K_F11)
    assert calls == [1] and saver.screensaver


def test_a_toolbar_size_click_stops_it_and_starts_that_size(saver):
    saver.start_screensaver()
    click(saver, "large")
    assert not saver.screensaver and saver.settings.difficulty == "large"


def test_a_pause_shorter_than_the_win_pulse_lets_the_pulse_finish(saver):
    from maze_game.round import WIN_PULSE_SECONDS
    saver.settings = replace(saver.settings, screensaver_pause=0)
    saver.start_screensaver()
    first = saver.round
    for _ in range(20000):
        saver.frame(1 / 60)
        if first.phase is Phase.WON:
            break
    while saver.round is first:
        assert first.time - first.won_at < WIN_PULSE_SECONDS + 0.1
        saver.frame(1 / 60)
    assert first.time - first.won_at >= WIN_PULSE_SECONDS and saver.screensaver


@pytest.mark.parametrize("action", ["large", "new"])
def test_a_toolbar_round_click_builds_one_maze(saver, monkeypatch, action):
    saver.start_screensaver()
    saver.frame(1 / 60)
    built = []
    real = game_app.Round
    monkeypatch.setattr(game_app, "Round", lambda *a, **kw: built.append(1) or real(*a, **kw))
    click(saver, action)
    assert len(built) == 1 and not saver.screensaver and saver.saver_path is None
    assert action != "large" or saver.settings.difficulty == "large"


def test_the_screensaver_button_toggles_it(saver):
    click(saver, "screensaver")
    assert saver.screensaver
    click(saver, "screensaver")
    assert not saver.screensaver


def test_screensaver_mode_uses_the_chosen_solver(saver, monkeypatch):
    from maze_game import app as app_module
    seen = []
    real = app_module.iter_solver_cells
    monkeypatch.setattr(app_module, "iter_solver_cells",
                        lambda grid, start, end, solver, lookahead, rng: (
                            seen.append((solver, lookahead)),
                            real(grid, start, end, solver, lookahead, rng))[1])
    saver.settings = replace(saver.settings, screensaver_solver="wall",
                             screensaver_lookahead=7)
    saver.start_screensaver()
    for _ in range(200):
        saver.frame(1 / 60)
        if seen:
            break
    assert seen[0] == ("wall", 7)


def test_toolbar_shows_screensaver_instead_of_stats(saver, monkeypatch):
    saver.start_screensaver()
    assert saver_state(saver, monkeypatch).screensaver
    drawn = []
    real = toolbar_module.text
    monkeypatch.setattr(toolbar_module, "text",
                        lambda surface, string, *a, **kw: (drawn.append(string),
                                                           real(surface, string, *a, **kw)))
    saver.frame(1 / 60)
    assert "Screensaver" in drawn
    assert not any(s.startswith("Explored") for s in drawn)


def test_a_solve_that_stops_short_moves_on_to_the_next_maze(saver, monkeypatch):
    real = game_app.iter_solver_cells
    monkeypatch.setattr(game_app, "iter_solver_cells",
                        lambda *a, **kw: itertools.islice(real(*a, **kw), 1))
    saver.start_screensaver()
    first = saver.round
    until_play(saver)
    for _ in range(30):
        saver.frame(1 / 60)
        if saver.round is not first:
            break
    assert saver.round is not first and saver.screensaver
