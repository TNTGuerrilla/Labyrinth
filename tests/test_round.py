import itertools
import random
from dataclasses import replace

from maze_game import round as round_module
from maze_game.assist import route
from maze_game.round import (HINT_SECONDS, SINGLE_HUE, WIN_OVERLAY_DELAY, Phase, Round)
from maze_game.steering import PathSteer
from tests.gameutil import FAST, grown
from tests.mazeutil import assert_perfect, bfs_path


def test_growth_makes_a_perfect_maze_then_play():
    r = grown()
    assert_perfect(r.grid)
    assert not r.heads
    assert r.shortest == len(bfs_path(r.grid, r.start, r.end)) - 1


def test_animated_growth_reports_changed_cells():
    r = Round(20, 12, FAST, random.Random(3))
    changed = set()
    for _ in range(3):
        changed |= r.update(1 / 60)
    assert changed and r.phase is Phase.GROW


def test_skip_growth_fast_forwards_within_the_budget():
    ticks = itertools.count()
    r = Round(40, 30, FAST, random.Random(2), clock=lambda: next(ticks) * 0.001)
    r.skip_growth()
    r.update(1 / 60)
    assert r.phase is Phase.GROW and 0 < len(r.region_of) < 1200
    for _ in range(10000):
        if r.phase is Phase.PLAY:
            break
        r.update(1 / 60)
    assert r.phase is Phase.PLAY
    assert_perfect(r.grid)


def test_instant_mode_starts_in_fast_forward():
    r = Round(6, 4, replace(FAST, animated=False), random.Random(4))
    assert r.fast_forward
    r.update(1 / 60)
    assert r.phase is Phase.PLAY


def test_no_moves_while_growing():
    r = Round(20, 12, FAST, random.Random(5))
    assert r.move(5.0, lambda c, came: None) == set() and r.explored == 0


def test_moves_count_cells_explored_and_build_the_trail():
    r = grown()
    path = route(r.grid, r.start, r.end)
    changed = r.move(10.0, PathSteer(path[1:3]).choose)
    assert r.explored == 2 and r.path.route == path[:3] and r.timer_running
    assert set(path[:3]) <= changed


def test_backtracking_does_not_count_again():
    r = grown()
    path = route(r.grid, r.start, r.end)
    r.move(10.0, PathSteer([path[1], path[2], path[1], path[2]]).choose)
    assert r.explored == 2


def test_returning_to_the_start_does_not_count():
    r = grown()
    path = route(r.grid, r.start, r.end)
    r.move(10.0, PathSteer([path[1], path[0]]).choose)
    assert r.explored == 1


def test_reaching_the_end_wins():
    r = grown()
    r.move(1000.0, PathSteer(route(r.grid, r.start, r.end)[1:]).choose)
    assert r.phase is Phase.WON and r.explored == r.shortest and r.efficiency == 100
    assert not r.timer_running
    assert r.mover.frm == r.end and not r.mover.moving


def test_assisted_cells_are_counted_separately():
    r = grown()
    r.move(1000.0, PathSteer(route(r.grid, r.start, r.end)[1:]).choose, assisted=True)
    assert r.explored == 0 and r.auto_explored == r.shortest and r.efficiency == 100


def test_auto_solve_only_counts_cells_the_player_had_not_entered():
    r = grown()
    path = route(r.grid, r.start, r.end)
    r.move(10.0, PathSteer(path[1:3]).choose)
    r.move(1000.0, PathSteer(path[3:]).choose, assisted=True)
    assert r.explored == 2 and r.auto_explored == r.shortest - 2


def test_efficiency_drops_with_detours():
    r = grown()
    path = route(r.grid, r.start, r.end)
    detour = next((n for c in path[1:-1] for n in r.grid.open_neighbors(c) if n not in path),
                  None)
    if detour is None:
        return  # this maze has no side branch on its route
    i = next(i for i, c in enumerate(path) if detour in r.grid.open_neighbors(c))
    steps = path[1:i + 1] + [detour, path[i]] + path[i + 1:]
    r.move(1000.0, PathSteer(steps).choose)
    assert r.explored == r.shortest + 1
    assert r.efficiency == round(100 * r.shortest / (r.shortest + 1))


def test_toward_end_leads_to_the_end():
    r = grown()
    c = r.start
    for _ in range(r.shortest):
        c = r.toward_end[c]
    assert c == r.end


def test_timer_starts_on_the_first_move():
    r = grown()
    r.tick_timer(1.0)
    assert r.elapsed == 0.0
    r.move(0.6, PathSteer(route(r.grid, r.start, r.end)[1:2]).choose)
    r.tick_timer(1.0)
    assert r.elapsed == 1.0


def test_replay_resets_play_but_keeps_the_maze():
    r = grown()
    walls = [r.grid.open_dirs(c) for c in r.grid.cells()]
    start, end = r.start, r.end
    r.move(1000.0, PathSteer(route(r.grid, r.start, r.end)[1:]).choose)
    r.assisted = True
    r.replay()
    assert r.phase is Phase.PLAY and r.explored == 0 and r.auto_explored == 0 and r.hints == 0 and r.elapsed == 0.0
    assert r.trail == {} and r.dot == start and r.end == end and not r.assisted
    assert [r.grid.open_dirs(c) for c in r.grid.cells()] == walls


def test_replay_is_ignored_while_growing():
    r = Round(20, 12, FAST, random.Random(6))
    r.replay()
    assert r.phase is Phase.GROW


def test_replay_forgets_visited_cells():
    r = grown()
    path = route(r.grid, r.start, r.end)
    r.move(10.0, PathSteer(path[1:3]).choose)
    r.replay()
    r.move(10.0, PathSteer(path[1:3]).choose)
    assert r.explored == 2


def test_hint_counts_and_expires():
    r = grown()
    r.hint(3)
    assert r.hints == 1 and r.hint_active
    assert r.hint_route == route(r.grid, r.start, r.end)[1:4]
    r.update(HINT_SECONDS + 0.01)
    assert not r.hint_active


def test_flash_and_win_overlay_timing():
    r = grown()
    r.flash()
    assert r.flash_active
    r.move(1000.0, PathSteer(route(r.grid, r.start, r.end)[1:]).choose)
    assert r.win_pulse_active and not r.win_overlay_visible
    r.update(WIN_OVERLAY_DELAY)
    assert r.win_overlay_visible


def test_multicolor_off_uses_one_hue():
    r = Round(10, 8, replace(FAST, multicolor=False), random.Random(7))
    assert set(r.hues) == {SINGLE_HUE}
    r.multicolor = True
    assert r.hues == r.region_hues


def test_build_until_then_finish_now():
    r = Round(20, 12, FAST, random.Random(8))
    assert r.build_until(0.8) >= 0.8 * 240
    assert r.phase is Phase.GROW
    r.finish_growth_now()
    assert r.phase is Phase.PLAY
    assert_perfect(r.grid)


def test_finish_growth_now_calls_back_between_chunks(monkeypatch):
    monkeypatch.setattr(round_module, "BUILD_CHUNK", 10)
    r = Round(20, 12, FAST, random.Random(8))
    calls = []
    r.finish_growth_now(on_chunk=lambda: calls.append(r.phase))
    assert r.phase is Phase.PLAY and calls and set(calls) == {Phase.GROW}
    assert_perfect(r.grid)


def test_has_the_attributes_draw_cell_reads():
    r = grown()
    for name in ("grid", "region_of", "hues", "welds", "trail", "head_cells", "start", "end",
                 "dot"):
        assert hasattr(r, name)


def test_head_cells_is_cached_and_tracks_the_heads_dict():
    r = Round(20, 12, FAST, random.Random(9))
    r.update(1 / 60)
    assert r.head_cells == set(r.heads.values())
    first = r.head_cells
    assert r.head_cells is first
    r.update(1 / 60)
    assert r.head_cells == set(r.heads.values())
