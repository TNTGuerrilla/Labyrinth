"""One maze round: growth, play, win. Pure logic with no pygame dependency.

Round exposes the attribute names maze_saver.render.draw_cell reads (grid, region_of,
hues, welds, trail, head_cells, start, end, dot), so the game draws it with the
screensaver's own cell code.
"""
from __future__ import annotations

import random
import time
from enum import Enum, auto
from typing import Callable, Optional

from maze_saver.board import WELD_FLASH_SECONDS, StepAccumulator, choose_endpoints
from maze_saver.maze import (Carve, Cell, Finish, GenEvent, Grid, Retreat, Start, Weld,
                             choose_generator, edge_key)

from .assist import toward_end
from .config import GameSettings
from .motion import Chooser, Mover
from .trail import Trail

SINGLE_HUE = 0.58  # steel blue, used for every region when multi-color is off
HINT_SECONDS = 2.0
FLASH_SECONDS = 1.5
WIN_PULSE_SECONDS = 1.0
WIN_OVERLAY_DELAY = 1.0
FAST_FORWARD_BUDGET = 0.004  # seconds of growth work per frame while fast-forwarding
FAST_FORWARD_CHUNK = 64  # events applied between clock checks
BUILD_CHUNK = 20000  # events between on_chunk calls in build_until and finish_growth_now


class Phase(Enum):
    GROW = auto()
    PLAY = auto()
    WON = auto()


class Round:
    def __init__(self, cols: int, rows: int, settings: GameSettings, rng: random.Random,
                 clock: Callable[[], float] = time.perf_counter):
        self._clock = clock
        self.grid = Grid(cols, rows)
        self.start, self.end = choose_endpoints(cols, rows, rng)
        count, self._gen = choose_generator(self.grid, rng, settings.max_leads)
        base = rng.random()
        self.region_hues = [(base + i / count) % 1.0 for i in range(count)]
        self.multicolor = settings.multicolor
        self.gen_speed = settings.gen_speed
        self.region_of: dict[Cell, int] = {}
        self.heads: dict[int, Cell] = {}
        self._head_cells: set = set()
        self.welds: dict = {}
        self.time = 0.0
        self.shortest = 0
        self._toward_end: dict[Cell, Cell] = {}
        self.phase = Phase.GROW
        self.fast_forward = not settings.animated
        self._active_leads = count
        self._steps = StepAccumulator(settings.gen_speed)
        self._reset_play()

    # --- drawing attributes -------------------------------------------------

    @property
    def multicolor(self) -> bool:
        return self._multicolor

    @multicolor.setter
    def multicolor(self, on: bool) -> None:
        self._multicolor = on
        self.hues = (list(self.region_hues) if on
                     else [SINGLE_HUE] * len(self.region_hues))

    @property
    def head_cells(self) -> set:
        return self._head_cells

    @property
    def trail(self) -> dict:
        return self.path.edges

    @property
    def dot(self) -> Cell:
        return self.mover.cell

    @property
    def toward_end(self) -> dict:
        """toward_end[c] is the neighbor one step closer to the end. Empty while growing."""
        return self._toward_end

    # --- growth ---------------------------------------------------------------

    def update(self, dt: float) -> set:
        """Advance the clock, expire weld flashes and run growth. Returns changed cells."""
        self.time += dt
        changed: set = set()
        for edge, until in list(self.welds.items()):
            if until <= self.time:
                del self.welds[edge]
                changed.update(edge)
        if self.phase is Phase.GROW:
            if self.fast_forward:
                self._fast_forward(changed)
            else:
                self._steps.rate = self.gen_speed * max(1, self._active_leads)
                for _ in range(self._steps.take(dt)):
                    if not self._step_growth(changed):
                        break
        return changed

    def skip_growth(self) -> None:
        if self.phase is Phase.GROW:
            self.fast_forward = True

    def build_until(self, fraction: float, on_chunk: Optional[Callable[[], None]] = None) -> int:
        """Apply growth synchronously until `fraction` of cells are carved (benchmark use).
        Returns the number of cells carved."""
        target = fraction * self.grid.cols * self.grid.rows
        scratch: set = set()
        count = 0
        while self.phase is Phase.GROW and len(self.region_of) < target:
            self._step_growth(scratch)
            scratch.clear()
            count += 1
            if on_chunk is not None and count % BUILD_CHUNK == 0:
                on_chunk()
        return len(self.region_of)

    def finish_growth_now(self, on_chunk: Optional[Callable[[], None]] = None) -> None:
        """Apply the rest of the growth synchronously. `on_chunk` runs every BUILD_CHUNK
        events, so a caller can keep reading input (it may raise to stop early)."""
        scratch: set = set()
        count = 0
        while self.phase is Phase.GROW:
            self._step_growth(scratch)
            scratch.clear()
            count += 1
            if on_chunk is not None and count % BUILD_CHUNK == 0:
                on_chunk()

    def _fast_forward(self, changed: set) -> None:
        deadline = self._clock() + FAST_FORWARD_BUDGET
        while self.phase is Phase.GROW:
            for _ in range(FAST_FORWARD_CHUNK):
                if not self._step_growth(changed):
                    return
            if self._clock() >= deadline:
                return

    def _step_growth(self, changed: set) -> bool:
        """Apply one generator event. Returns False once growth has finished."""
        event = next(self._gen, None)
        if event is None:
            self._finish_growth()
            return False
        self._apply(event, changed)
        return True

    def _finish_growth(self) -> None:
        self.heads.clear()
        self._head_cells.clear()
        self._toward_end = toward_end(self.grid, self.end)
        self.shortest = self._steps_to_end(self.start)
        self.phase = Phase.PLAY

    def _steps_to_end(self, cell: Cell) -> int:
        steps = 0
        c = cell
        while c != self.end:
            c = self._toward_end[c]
            steps += 1
        return steps

    def _set_head(self, region: int, cell: Cell) -> None:
        old = self.heads.get(region)
        if old is not None:
            self._head_cells.discard(old)
        self.heads[region] = cell
        self._head_cells.add(cell)

    def _pop_head(self, region: int) -> None:
        old = self.heads.pop(region, None)
        if old is not None:
            self._head_cells.discard(old)

    def _apply(self, event: GenEvent, changed: set) -> None:
        if isinstance(event, Start):
            self.region_of[event.cell] = event.region
            self._set_head(event.region, event.cell)
            changed.add(event.cell)
        elif isinstance(event, Carve):
            self.region_of[event.b] = event.region
            self._set_head(event.region, event.b)
            changed.update((event.a, event.b))
        elif isinstance(event, Retreat):
            self._set_head(event.region, event.to)
            changed.update((event.frm, event.to))
        elif isinstance(event, Finish):
            self._pop_head(event.region)
            self._active_leads = max(0, self._active_leads - 1)
            changed.add(event.cell)
        elif isinstance(event, Weld):
            self.welds[edge_key(event.a, event.b)] = self.time + WELD_FLASH_SECONDS
            changed.update((event.a, event.b))

    # --- play -----------------------------------------------------------------

    def _reset_play(self) -> None:
        self.mover = Mover(self.start)
        self.path = Trail(self.start)
        self.explored = 0
        self.auto_explored = 0
        self._visited: set = {self.start}
        self.hints = 0
        self.elapsed = 0.0
        self.timer_running = False
        self.assisted = False
        self.won_at: Optional[float] = None
        self.hint_route: list = []
        self.hint_at: Optional[float] = None
        self.flash_at: Optional[float] = None

    def move(self, distance: float, choose: Chooser, assisted: bool = False) -> set:
        """Glide up to `distance` cells. Returns cells whose drawing changed."""
        changed: set = set()
        if self.phase is not Phase.PLAY:
            return changed
        for a, b in self.mover.advance(distance, choose):
            self.path.move(a, b)
            if b not in self._visited:
                self._visited.add(b)
                if assisted:
                    self.auto_explored += 1
                else:
                    self.explored += 1
            self.timer_running = True
            changed.update((a, b))
            if b == self.end:
                self.phase = Phase.WON
                self.timer_running = False
                self.won_at = self.time
                self.mover.place(self.end)
                break
        return changed

    def reverse(self) -> None:
        if self.phase is Phase.PLAY:
            self.mover.reverse()

    def tick_timer(self, dt: float) -> None:
        if self.timer_running:
            self.elapsed += dt

    def hint(self, length: int) -> None:
        if self.phase is not Phase.PLAY:
            return
        route: list = []
        c = self.mover.cell
        for _ in range(length):
            if c == self.end:
                break
            c = self._toward_end[c]
            route.append(c)
        self.hint_route = route
        self.hints += 1
        self.hint_at = self.time

    def flash(self) -> None:
        if self.phase is not Phase.GROW:
            self.flash_at = self.time

    def replay(self) -> None:
        if self.phase is Phase.GROW:
            return
        self._reset_play()
        self.phase = Phase.PLAY

    @property
    def efficiency(self) -> int:
        total = self.explored + self.auto_explored
        return round(100 * self.shortest / total) if total else 0

    @property
    def hint_active(self) -> bool:
        return self.hint_at is not None and self.time - self.hint_at < HINT_SECONDS

    @property
    def flash_active(self) -> bool:
        return self.flash_at is not None and self.time - self.flash_at < FLASH_SECONDS

    @property
    def win_pulse_active(self) -> bool:
        return (self.phase is Phase.WON and self.won_at is not None
                and self.time - self.won_at < WIN_PULSE_SECONDS)

    @property
    def win_overlay_visible(self) -> bool:
        return (self.phase is Phase.WON and self.won_at is not None
                and self.time - self.won_at >= WIN_OVERLAY_DELAY)
