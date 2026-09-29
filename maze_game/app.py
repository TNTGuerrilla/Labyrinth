"""The game window: main loop, input routing and dialogs."""
from __future__ import annotations

import math
import random
import time
import webbrowser
from dataclasses import replace
from pathlib import Path
from typing import Optional, Union

import pygame

from maze_saver.icon import load_icon
from maze_saver.maze import E, N, S, W
from labyrinth_update.info import LICENSE_URL, REPO_URL, status_text
from labyrinth_update.install import install_game, relaunch
from labyrinth_update.updater import AVAILABLE, DOWNLOADING, FAILED, READY, Updater
from labyrinth_update.version import running_version

from . import benchmark, config, difficulty
from .assist import route
from .camera import Camera
from .config import GameSettings
from .game_render import GameRenderer
from .keymap import Keymap
from .round import Phase, Round
from .steering import AutoSteer, KeyboardSteer, PathSteer, dash_path, is_reverse, steer_toward
from .ui.custom_dialog import CustomDialog
from .ui.settings_model import InfoState, SettingsModel
from .ui.settings_panel import SettingsPanel
from .ui.toolbar import TOOLBAR_H, Toolbar, ToolbarState
from .ui.whats_new_dialog import WhatsNewDialog
from .ui.widgets import draw_progress
from .ui.win_screen import WinScreen

TITLE = "Labyrinth"
open_browser = webbrowser.open  # the default browser; tests replace it
LINKS = {"github": REPO_URL, "license": LICENSE_URL}
START_SIZE = (1280, 720)
MIN_SIZE = (960, 540)
FPS_CAP = 120
MAX_DT = 0.1  # a stalled frame never jumps the dot more than this much time
DASH_MULTIPLIER = 3.0
CLICK_SECONDS = 0.2
DRAG_PX = 6
KEY_REPEAT = (350, 35)  # only while a dialog is open
DIRS = {"up": N, "left": W, "down": S, "right": E}
GROW_ACTIONS = frozenset({"confirm", "new", "small", "medium", "large", "xl", "custom",
                          "settings", "fullscreen", "colors", "update", "update_dismiss"})
NAV_KEYS = {"up": "up", "down": "down", "left": "left", "right": "right", "return": "confirm",
            "enter": "confirm", "space": "confirm", "escape": "cancel", "tab": "tab",
            "backspace": "backspace"}
FIXED_NAV_KEYS = {"return": "confirm", "enter": "confirm", "space": "confirm", "escape": "cancel",
                  "tab": "tab", "backspace": "backspace"}

Dialog = Union[CustomDialog, SettingsPanel, WhatsNewDialog]

BENCH_WINDOW_EVENTS = frozenset({
    pygame.WINDOWSIZECHANGED, pygame.WINDOWMINIMIZED, pygame.WINDOWRESTORED,
    pygame.WINDOWMAXIMIZED, pygame.WINDOWSHOWN, pygame.WINDOWFOCUSLOST,
    pygame.WINDOWFOCUSGAINED,
})


class BenchmarkCancelled(Exception):
    """Esc pressed, or the window closed, while the benchmark was running."""


def nav_for(key_name: str, keymap: Keymap) -> Optional[str]:
    """Dialog navigation for a key: Enter/Space, Esc, Tab, Backspace and digits (main row
    or keypad) are fixed and always win, so rebinding a movement action to one of those
    keys can never break dialog navigation. Otherwise the movement bindings and arrows."""
    if key_name in FIXED_NAV_KEYS:
        return FIXED_NAV_KEYS[key_name]
    if len(key_name) == 1 and key_name.isdigit():
        return "digit:" + key_name
    if len(key_name) == 3 and key_name[0] == "[" and key_name[1].isdigit():
        return "digit:" + key_name[1]
    action = keymap.action_for(key_name)
    if action in DIRS:
        return action
    if key_name in NAV_KEYS:
        return NAV_KEYS[key_name]
    return None


class Game:
    def __init__(self, settings: GameSettings, keymap: Keymap,
                 config_path: Optional[Path] = None, updater: Optional[Updater] = None):
        self.settings = settings
        self.keymap = keymap
        self.config_path = config_path
        self.updater = updater
        self.version = updater.current if updater is not None else (running_version("game") or "")
        self.rng = random.Random()
        self.window = pygame.Window(TITLE, START_SIZE, resizable=True)
        icon = load_icon()
        if icon is not None:
            self.window.set_icon(icon)
        self.window.minimum_size = MIN_SIZE
        self.window.maximize()
        pygame.event.pump()
        self.screen = self.window.get_surface()
        self.toolbar = Toolbar()
        self.win_screen = WinScreen()
        self.keys = KeyboardSteer()
        self.auto: Optional[AutoSteer] = None
        self.dash: Optional[PathSteer] = None
        self.press: Optional[tuple[float, tuple[int, int]]] = None
        self.dragging = False
        self.dialog: Optional[Dialog] = None
        self.minimized = False
        self.fullscreen = False
        self.running = True
        self.renderer = GameRenderer(self.play_rect.size)
        self.renderer.show_grid = self.settings.show_grid
        self.new_round()
        self._dialog_below: Optional[Dialog] = None  # the dialog a What's new panel covers
        shown = updater.start_whats_new() if updater is not None else None
        if shown is not None:
            self._open_dialog(WhatsNewDialog(f"Labyrinth updated to {shown.version}",
                                             shown.lines(), first_run=True))

    @property
    def play_rect(self) -> pygame.Rect:
        w, h = self.screen.get_size()
        return pygame.Rect(0, TOOLBAR_H, w, max(1, h - TOOLBAR_H))

    def save(self) -> None:
        try:
            config.save(self.settings, self.keymap, self.config_path)
        except OSError:
            pass

    # --- rounds -----------------------------------------------------------------

    def new_round(self, level: Optional[str] = None) -> None:
        if level is not None and level != self.settings.difficulty:
            self.settings = replace(self.settings, difficulty=level)
            self.save()
        pr = self.play_rect
        s = self.settings
        short = difficulty.pick_short(s.difficulty, s.custom_min, s.custom_max, pr.w, pr.h,
                                      self.rng)
        cols, rows = difficulty.grid_size(short, pr.w, pr.h)
        self.round = Round(cols, rows, s, self.rng)
        self.camera = Camera(cols, rows, pr.w, pr.h)
        self.renderer.invalidate()
        self._stop_assists()
        self.keys.reset_round()

    def replay(self) -> None:
        if self.round.phase is Phase.GROW:
            return
        self.round.replay()
        self.camera.reset_zoom()
        self.renderer.invalidate()
        self._stop_assists()
        self.keys.reset_round()

    def _stop_assists(self) -> None:
        self.auto = None
        self.dash = None
        self.press = None
        self.dragging = False

    def _toggle_auto(self) -> None:
        if self.auto is not None:
            self.auto = None
            return
        r = self.round
        if r.phase is not Phase.PLAY:
            return
        self.dash = None
        self.press = None
        self.dragging = False
        self.keys.forget_position()
        self.auto = AutoSteer(r.toward_end, r.end)
        r.assisted = True

    def do(self, action: str) -> None:
        r = self.round
        if r.phase is Phase.GROW and action not in GROW_ACTIONS:
            return
        if action == "confirm":
            if r.phase is Phase.GROW:
                r.skip_growth()
            elif r.win_overlay_visible:
                self.new_round()
        elif action == "new":
            self.new_round()
        elif action in difficulty.PRESETS:
            self.new_round(action)
        elif action == "custom":
            self._open_custom()
        elif action == "replay":
            self.replay()
        elif action == "hint":
            r.hint(self.settings.hint_length)
        elif action == "autosolve":
            self._toggle_auto()
        elif action == "flash":
            r.flash()
        elif action == "colors":
            self.settings = replace(self.settings, multicolor=not self.settings.multicolor)
            r.multicolor = self.settings.multicolor
            self.renderer.invalidate(clear=False)
            self.save()
        elif action == "zoom_in":
            self.camera.zoom_by(1, r.mover.position())
        elif action == "zoom_out":
            self.camera.zoom_by(-1, r.mover.position())
        elif action == "zoom_reset":
            self.camera.reset_zoom()
        elif action == "update":
            self._start_update()
        elif action == "update_dismiss":
            if self.updater is not None:
                self.updater.dismiss()
        elif action == "settings":
            self._open_settings()
        elif action == "fullscreen":
            self._toggle_fullscreen()

    # --- updates ----------------------------------------------------------------

    def _start_update(self) -> None:
        u = self.updater
        if u is None or u.target is None:
            return
        target = u.target
        u.install(lambda release, progress: install_game(release, target, progress))

    def _info_state(self) -> InfoState:
        u = self.updater
        if u is None:
            return InfoState(self.version)
        snap = u.snapshot
        return InfoState(self.version, True, status_text(snap, u.check_report),
                         snap.status in (AVAILABLE, FAILED))

    def _update_fields(self) -> dict:
        """The toolbar's update button for the updater's current state."""
        u = self.updater
        if u is None:
            return {}
        snap = u.snapshot
        version = snap.release.version if snap.release is not None else ""
        if snap.status == AVAILABLE:
            return dict(update_label=f"Update to {version}", update_short="Update",
                        update_tip=f"Labyrinth {version} is available. Click to install it "
                                   "and restart.",
                        update_dismiss=True)
        if snap.status == DOWNLOADING:
            percent = int(snap.progress * 100)
            return dict(update_label=f"Downloading {percent}%", update_short=f"{percent}%",
                        update_tip=f"Downloading Labyrinth {version}")
        if snap.status == READY:
            return dict(update_label="Restarting", update_short="Restarting")
        if snap.status == FAILED:
            return dict(update_label="Update failed", update_short="Failed",
                        update_tip=f"{snap.message} Click to try again.", update_dismiss=True)
        return {}

    def _restart(self) -> None:
        """The new version is in place: start it and close this one. If it cannot be
        started, closing still leaves the new version to run next time."""
        self.save()
        try:
            relaunch(self.updater.target)
        except OSError:
            pass
        self.running = False

    # --- events -----------------------------------------------------------------

    def handle(self, event: pygame.event.Event) -> None:
        t = event.type
        if t == pygame.QUIT:
            self.running = False
        elif t == pygame.WINDOWSIZECHANGED:
            self._resized()
        elif t == pygame.WINDOWMINIMIZED:
            self.minimized = True
        elif t in (pygame.WINDOWRESTORED, pygame.WINDOWMAXIMIZED, pygame.WINDOWSHOWN,
                  pygame.WINDOWFOCUSGAINED):
            self.minimized = False
        elif t == pygame.WINDOWFOCUSLOST:
            self.keys.clear()
            self.press = None
            self.dragging = False
        elif t == pygame.KEYDOWN:
            self._key_down(pygame.key.name(event.key))
        elif t == pygame.KEYUP:
            self._key_up(pygame.key.name(event.key))
        elif t == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._mouse_down(event.pos)
        elif t == pygame.MOUSEBUTTONUP and event.button == 1:
            self._mouse_up(event.pos)
        elif t == pygame.MOUSEMOTION:
            self._mouse_motion(event.pos)
        elif t == pygame.MOUSEWHEEL:
            self._wheel(event.y)

    def _key_down(self, name: str) -> None:
        if self.dialog is not None:
            self._dialog_key(name)
            return
        action = self.keymap.action_for(name)
        if action in DIRS:
            d = DIRS[action]
            self.keys.press(d)
            self._stop_assists()
            r = self.round
            if r.phase is Phase.PLAY and is_reverse(r.mover.frm, r.mover.to, d):
                r.reverse()
                self.keys.request = None
        elif action is not None:
            self.do(action)

    def _key_up(self, name: str) -> None:
        action = self.keymap.action_for(name)
        if action in DIRS:
            self.keys.release(DIRS[action])

    def _mouse_down(self, pos: tuple[int, int]) -> None:
        if self.dialog is not None:
            self._dialog_outcome(self.dialog.click(pos))
            return
        action = self.toolbar.action_at(pos)
        if action is not None:
            self.do(action)
            return
        r = self.round
        if r.win_overlay_visible:
            choice = self.win_screen.click(pos)
            if choice == "replay":
                self.replay()
            elif choice == "new":
                self.new_round()
            return
        if r.phase is Phase.PLAY and self.play_rect.collidepoint(pos):
            self.auto = None
            self.dash = None
            self.press = (time.monotonic(), pos)
            self.dragging = False
            self.keys.forget_position()

    def _mouse_motion(self, pos: tuple[int, int]) -> None:
        if self.press is not None and not self.dragging:
            x, y = self.press[1]
            if math.hypot(pos[0] - x, pos[1] - y) > DRAG_PX:
                self.dragging = True

    def _mouse_up(self, pos: tuple[int, int]) -> None:
        if self.press is not None and not self.dragging:
            self._dash_to(pos)
        self.press = None
        self.dragging = False

    def _dash_to(self, pos: tuple[int, int]) -> None:
        r = self.round
        pr = self.play_rect
        x, y = self.camera.to_cells(pos[0] - pr.x, pos[1] - pr.y)
        path = dash_path(r.grid, r.mover.next_center, (math.floor(x), math.floor(y)))
        if path:
            self.dash = PathSteer(path)
            self.keys.forget_position()

    def _wheel(self, y: int) -> None:
        if self.dialog is not None:
            wheel = getattr(self.dialog, "wheel", None)
            if wheel is not None and y:
                wheel(y)
            return
        if self.round.phase is not Phase.GROW and y:
            self.camera.zoom_by(y, self.round.mover.position())

    # --- per frame --------------------------------------------------------------

    def _driver(self):
        """(chooser, speed in cells/s, counts as assisted) for this frame."""
        r = self.round
        s = self.settings
        if self.auto is not None:
            return self.auto.choose, s.solve_speed, True
        if self.dash is not None:
            return self.dash.choose, s.glide_speed * DASH_MULTIPLIER, False
        if self.dragging:
            pr = self.play_rect
            mx, my = pygame.mouse.get_pos()
            target = self.camera.to_cells(mx - pr.x, my - pr.y)
            return (lambda c, came: steer_toward(r.grid, c, target)), s.glide_speed, False
        stops = (r.start, r.end)
        return ((lambda c, came: self.keys.choose(r.grid, c, came, s.follow_bends, stops,
                                                   r.end, s.lookahead, s.turn_pause)),
                s.glide_speed, False)

    def frame(self, dt: float) -> None:
        if self.updater is not None and self.updater.snapshot.status == READY:
            self._restart()
            return
        r = self.round
        before = r.phase
        self.keys.tick(dt)
        changed = r.update(dt)
        if before is Phase.GROW and r.phase is Phase.PLAY:
            # A turn request buffered while the player could not yet see the maze
            # (or held down through growth) must not fire on the first PLAY frame.
            self.keys.reset_round()
        if self.dialog is None and r.phase is Phase.PLAY and not self.minimized:
            if (self.press is not None and not self.dragging
                    and time.monotonic() - self.press[0] > CLICK_SECONDS):
                self.dragging = True
            choose, speed, assisted = self._driver()
            changed |= r.move(dt * speed, choose, assisted)
            if r.phase is not Phase.PLAY:
                self.auto = None
                self.dash = None
            else:
                if self.auto is not None and self.auto.done:
                    self.auto = None
                if self.dash is not None and self.dash.done and not r.mover.moving:
                    self.dash = None
            r.tick_timer(dt)
        if r.phase is not before:
            self.renderer.invalidate(clear=False)
        self.camera.follow(r.mover.position(), dt)
        self.draw(changed)

    def draw(self, changed: set) -> None:
        r = self.round
        pr = self.play_rect
        self.renderer.render(self.screen, pr, r, self.camera, changed)
        if r.win_overlay_visible:
            self.win_screen.draw(self.screen, pr, r, self.keymap)
        state = ToolbarState(self.settings.difficulty, self.auto is not None,
                             self.settings.multicolor, r.explored, r.elapsed,
                             **self._update_fields())
        mouse = pygame.mouse.get_pos() if self.dialog is None else (-1, -1)
        self.toolbar.draw(self.screen, self.keymap, state, mouse)
        if self.dialog is not None:
            if isinstance(self.dialog, SettingsPanel):
                self.dialog.model.set_info(self._info_state())
            self.dialog.draw(self.screen)
        self.window.flip()

    # --- window -----------------------------------------------------------------

    def _resized(self) -> None:
        self.screen = self.window.get_surface()
        pr = self.play_rect
        self.camera.resize(pr.w, pr.h)
        self.renderer.resize(pr.size)

    def _toggle_fullscreen(self) -> None:
        if self.fullscreen:
            self.window.set_windowed()
        else:
            self.window.set_fullscreen(desktop=True)
        self.fullscreen = not self.fullscreen
        # The window's WINDOWSIZECHANGED event covers the resulting resize; calling
        # _resized() here too would double it (see the resize() preview bug in
        # game_render.py).

    # --- dialogs ----------------------------------------------------------------

    def _bench_for_screen(self) -> tuple[Optional[int], Optional[float]]:
        s = self.settings
        pr = self.play_rect
        if s.bench_size is not None and s.bench_resolution == (pr.w, pr.h):
            return s.bench_size, s.bench_rate
        return None, None

    def _open_dialog(self, dialog: Dialog) -> None:
        self.dialog = dialog
        self.keys.clear()
        self.press = None
        self.dragging = False
        pygame.key.set_repeat(*KEY_REPEAT)

    def _close_dialog(self) -> None:
        closed = self.dialog
        self.dialog, self._dialog_below = self._dialog_below, None
        if isinstance(closed, WhatsNewDialog) and closed.first_run and self.updater is not None:
            self.updater.mark_whats_new_seen()  # closing it is what counts as seen
        if self.dialog is None:
            pygame.key.set_repeat()

    def _open_custom(self) -> None:
        s = self.settings
        pr = self.play_rect
        size, rate = self._bench_for_screen()
        self._open_dialog(CustomDialog(s.custom_min, s.custom_max,
                                       difficulty.ceiling(pr.w, pr.h), size, rate,
                                       (pr.w, pr.h)))

    def _open_settings(self) -> None:
        if self.updater is not None:
            self.updater.check(force=True)
        pr = self.play_rect
        model = SettingsModel(self.settings, self.keymap, difficulty.ceiling(pr.w, pr.h),
                              (pr.w, pr.h), info=self._info_state())
        self._open_dialog(SettingsPanel(model))

    def _dialog_key(self, name: str) -> None:
        d = self.dialog
        if isinstance(d, SettingsPanel) and d.capturing:
            d.capture(name)
            return
        nav = nav_for(name, self.keymap)
        if nav is not None:
            self._dialog_outcome(d.handle(nav, time.monotonic()))

    def _dialog_outcome(self, outcome: Optional[str]) -> None:
        d = self.dialog
        if outcome in ("close", "cancel"):
            self._close_dialog()
        elif outcome == "start":
            lo, hi = d.result()
            self.settings = replace(self.settings, difficulty="custom", custom_min=lo,
                                    custom_max=hi)
            self.save()
            self._close_dialog()
            self.new_round()
        elif outcome == "apply":
            self.settings, self.keymap = d.model.result()
            self.save()
            if self.updater is not None:
                self.updater.set_enabled(self.settings.check_updates)
            r = self.round
            r.multicolor = self.settings.multicolor
            r.gen_speed = self.settings.gen_speed
            self.renderer.show_grid = self.settings.show_grid
            self.renderer.invalidate(clear=False)
            self._close_dialog()
        elif outcome == "benchmark":
            if self.run_benchmark() is None:
                return
            s = self.settings
            if isinstance(d, CustomDialog):
                d.bench_size, d.bench_rate = s.bench_size, s.bench_rate
            else:
                d.model.draft = replace(d.model.draft, bench_size=s.bench_size,
                                        bench_rate=s.bench_rate,
                                        bench_resolution=s.bench_resolution)
        elif outcome in LINKS:
            open_browser(LINKS[outcome])
        elif outcome == "check_now":
            if self.updater is not None:
                self.updater.check_now()
        elif outcome == "update":
            self._start_update()  # progress shows in the status line and on the toolbar
        elif outcome == "whats_new":
            if self.updater is not None:
                shown = self.updater.running_whats_new()
                below = self.dialog
                self._open_dialog(WhatsNewDialog(f"Labyrinth updated to {shown.version}",
                                                 shown.lines()))
                self._dialog_below = below  # Esc or OK returns to Settings

    # --- benchmark --------------------------------------------------------------

    def run_benchmark(self) -> Optional[int]:
        """Find the recommended Custom size for this play area and save it with the build
        rate. Returns the size, or None if cancelled."""
        pr = self.play_rect
        tested: list[int] = []
        rates: list[float] = []

        def measure(n: int) -> float:
            times, rate = self._bench_scene(n, len(tested))
            rates.append(rate)
            return benchmark.score(times)

        try:
            size = benchmark.find_recommended(measure, difficulty.ceiling(pr.w, pr.h),
                                              on_step=tested.append)
        except BenchmarkCancelled:
            return None
        self.settings = replace(self.settings, bench_size=size,
                                bench_rate=benchmark.median(rates),
                                bench_resolution=(pr.w, pr.h))
        self.save()
        return size

    def _bench_scene(self, n: int, index: int) -> tuple[list[float], float]:
        """The benchmark scene for short side n at 100% zoom. Returns the frame times of
        the rendered part and the build rate in seconds per cell."""
        pr = self.play_rect
        cols, rows = difficulty.grid_size(n, pr.w, pr.h)
        s = replace(self.settings, animated=True)
        rng = random.Random(n)
        label = f"Measuring performance: {n} cells (test {index})"
        draw_progress(self.screen, pr, label, 0.0)
        self.window.flip()
        scene = Round(cols, rows, s, rng)
        started = time.perf_counter()
        carved = scene.build_until(benchmark.BUILD_FRACTION, on_chunk=self._bench_events)
        rate = (time.perf_counter() - started) / max(1, carved)
        scene.skip_growth()
        camera = Camera(cols, rows, pr.w, pr.h)
        renderer = GameRenderer(pr.size)
        renderer.show_grid = self.settings.show_grid
        times: list[float] = []
        self._bench_events()
        last = time.perf_counter()

        def show(changed: set, fraction: float) -> None:
            nonlocal last
            renderer.render(self.screen, pr, scene, camera, changed)
            draw_progress(self.screen, pr, label, fraction)
            self.window.flip()
            self._bench_events()
            now = time.perf_counter()
            times.append(now - last)
            last = now

        phase_start = last
        while (scene.phase is Phase.GROW
               and last - phase_start < benchmark.FINISH_SECONDS):
            dt = times[-1] if times else 0.0
            show(scene.update(dt), 0.5 * (last - phase_start) / benchmark.FINISH_SECONDS)
        scene.finish_growth_now()
        steer = PathSteer(route(scene.grid, scene.start, scene.end)[1:])
        last = phase_start = time.perf_counter()
        while scene.phase is Phase.PLAY and last - phase_start < benchmark.RUN_SECONDS:
            dt = times[-1] if times else 0.0
            changed = scene.update(dt) | scene.move(dt * s.solve_speed, steer.choose, True)
            show(changed, 0.5 + 0.5 * (last - phase_start) / benchmark.RUN_SECONDS)
        return times, rate

    def _bench_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.event.post(pygame.event.Event(pygame.QUIT))
                raise BenchmarkCancelled
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                raise BenchmarkCancelled
            if event.type in BENCH_WINDOW_EVENTS:
                self.handle(event)
                if event.type == pygame.WINDOWSIZECHANGED:
                    # The result would be for a size that no longer applies.
                    raise BenchmarkCancelled


def run(settings: GameSettings, keymap: Keymap, config_path: Optional[Path] = None,
        updater: Optional[Updater] = None) -> None:
    game = Game(settings, keymap, config_path, updater)
    clock = pygame.time.Clock()
    while game.running:
        dt = min(clock.tick(FPS_CAP) / 1000.0, MAX_DT)
        for event in pygame.event.get():
            game.handle(event)
        if game.running:
            game.frame(dt)
