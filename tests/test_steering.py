import random

from maze_saver.maze import E, N, S, W, Grid
from maze_game.steering import (AutoSteer, KeyboardSteer, PathSteer, dash_path, is_reverse,
                                steer_toward)
from tests.gameutil import fork_grid


def held(*dirs):
    k = KeyboardSteer()
    for d in dirs:
        k.press(d)
    return k


def grid_of(cols, rows, edges):
    g = Grid(cols, rows)
    for a, b in edges:
        g.carve(a, b)
    return g


CROSS = (((0, 1), (1, 1)), ((1, 1), (2, 1)), ((1, 1), (1, 0)), ((1, 1), (1, 2)))
TEE = (((0, 1), (1, 1)), ((1, 1), (1, 0)), ((1, 1), (1, 2)))
BEND = (((0, 0), (1, 0)), ((1, 0), (1, 1)))
STRAIGHT = (((0, 1), (1, 1)), ((1, 1), (2, 1)))
TRIFORK = (((0, 1), (1, 1)), ((1, 1), (2, 1)), ((1, 1), (1, 0)))  # W(came)-E-N open, S closed
FAR = (9, 9)  # an end cell outside these little grids


def guided(k, g, cell, came, lookahead=0, stops=()):
    return k.choose(g, cell, came, True, stops, FAR, lookahead, 0.2)


def held_since_before(*dirs):
    """Keys held with their press already used up (no pending request)."""
    k = held(*dirs)
    k.request = None
    return k


def test_classic_mode_is_unchanged():
    g = fork_grid()
    assert held(E).choose(g, (0, 0), None, False, (), FAR, 4, 0.2) == (1, 0)
    assert held(W).choose(g, (0, 0), (1, 0), False, (), FAR, 4, 0.2) is None
    assert KeyboardSteer().choose(g, (0, 0), None, False, (), FAR, 4, 0.2) is None


def test_latest_press_wins_and_release_falls_back():
    k = held(E, S)
    assert k.wanted == S and k.request == S
    k.release(S)
    assert k.wanted == E
    k.clear()
    assert k.wanted is None and k.request is None


def test_fresh_press_is_taken_at_once():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    k.press(S)
    assert guided(k, g, (1, 1), (0, 1)) == (1, 2)
    assert k.request is None


def test_fork_pauses_then_carries_straight_on():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    assert guided(k, g, (1, 1), (0, 1)) is None
    k.tick(0.1)
    assert guided(k, g, (1, 1), (0, 1)) is None
    k.tick(0.15)
    assert guided(k, g, (1, 1), (0, 1)) == (2, 1)


def test_press_during_the_fork_pause_turns():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    assert guided(k, g, (1, 1), (0, 1)) is None
    k.press(N)
    assert guided(k, g, (1, 1), (0, 1)) == (1, 0)


def test_letting_go_during_the_pause_stops():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    guided(k, g, (1, 1), (0, 1))
    k.release(E)
    k.tick(1.0)
    assert guided(k, g, (1, 1), (0, 1)) is None


def test_t_junction_waits_for_a_press():
    g = grid_of(3, 3, TEE)
    k = held_since_before(E)
    guided(k, g, (1, 1), (0, 1))
    k.tick(1.0)
    assert guided(k, g, (1, 1), (0, 1)) is None
    k.press(S)
    assert guided(k, g, (1, 1), (0, 1)) == (1, 2)


def test_corridor_bends_flow_without_a_pause():
    g = grid_of(2, 2, BEND)
    k = held_since_before(E)
    assert guided(k, g, (1, 0), (0, 0)) == (1, 1)


def test_stale_request_is_dropped_at_a_bend():
    g = grid_of(2, 2, BEND)
    k = held_since_before(E)
    k.request = N  # pressed earlier, not usable here
    assert guided(k, g, (1, 0), (0, 0)) == (1, 1)
    assert k.request is None


def test_obvious_dead_ends_are_not_choices():
    g = grid_of(4, 2, (((0, 0), (1, 0)), ((1, 0), (2, 0)), ((2, 0), (3, 0)), ((1, 0), (1, 1))))
    k = held_since_before(E)
    assert k.choose(g, (1, 0), (0, 0), True, (), (3, 0), 4, 0.2) == (2, 0)


def test_corridor_keeps_advancing_into_an_obvious_dead_end():
    """Pruning classifies forks; it must not stall a plain corridor that itself
    happens to dead-end within the look-ahead distance."""
    edges = [((i, 0), (i + 1, 0)) for i in range(8)]
    g = grid_of(9, 1, edges)
    k = held_since_before(E)
    assert guided(k, g, (1, 0), (0, 0), lookahead=12) == (2, 0)


def test_press_into_a_wall_at_rest_does_nothing():
    g = grid_of(3, 2, STRAIGHT)
    k = held_since_before(E)
    k.release(E)
    assert guided(k, g, (1, 1), (0, 1)) is None  # comes to rest, nothing held
    k.press(N)  # closed here
    assert guided(k, g, (1, 1), (0, 1)) is None
    assert k.request is None
    assert guided(k, g, (1, 1), (0, 1)) is None  # frame 2: N still held, still no move
    assert guided(k, g, (1, 1), (0, 1)) is None  # frame 3: still no move
    k.press(W)  # a fresh, open press (back the way it came)
    assert guided(k, g, (1, 1), (0, 1)) == (0, 1)


def test_press_into_a_wall_at_a_stopped_fork_does_nothing():
    g = grid_of(3, 3, TEE)
    k = held_since_before(E)
    guided(k, g, (1, 1), (0, 1))  # starts the pause
    k.tick(1.0)
    assert guided(k, g, (1, 1), (0, 1)) is None  # pause elapsed, E is closed, stops
    k.press(E)  # still closed
    assert guided(k, g, (1, 1), (0, 1)) is None
    assert k.request is None
    assert guided(k, g, (1, 1), (0, 1)) is None  # frame 2: E still held, still no move
    assert guided(k, g, (1, 1), (0, 1)) is None  # frame 3: still no move
    k.press(N)  # open
    assert guided(k, g, (1, 1), (0, 1)) == (1, 0)


def test_stopped_dot_ignores_a_held_key_without_a_fresh_press():
    """The idle chooser is asked again every frame; merely still being held (with
    no new press behind it) must not resume movement after a genuine stop."""
    g = grid_of(3, 2, STRAIGHT)
    k = held_since_before(E)
    k.release(E)
    assert guided(k, g, (1, 1), (0, 1)) is None  # nothing held, genuinely stops
    k.held.append(E)  # held again, but no fresh press: request stays None
    assert guided(k, g, (1, 1), (0, 1)) is None
    assert guided(k, g, (1, 1), (0, 1)) is None
    k.press(E)  # a real, fresh press of the same, now-open direction
    assert guided(k, g, (1, 1), (0, 1)) == (2, 1)


def test_pressing_a_closed_direction_during_the_pause_still_carries_on():
    g = grid_of(3, 3, TRIFORK)
    k = held_since_before(E)
    assert guided(k, g, (1, 1), (0, 1)) is None  # starts the pause
    k.press(S)  # closed here; must not derail the eventual straight continuation
    assert guided(k, g, (1, 1), (0, 1)) is None  # still paused
    k.tick(1.0)
    assert guided(k, g, (1, 1), (0, 1)) == (2, 1)  # carries straight on once it elapses


def test_pause_resets_if_the_fork_is_left_by_other_means():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    assert guided(k, g, (1, 1), (0, 1)) is None  # starts the pause at the fork
    guided(k, g, (2, 1), (1, 1))  # dot leaves the fork by some other means
    k.tick(1.0)
    assert guided(k, g, (1, 1), (0, 1)) is None  # pauses again, doesn't skip through


def test_start_and_finish_stop_the_dot():
    g = grid_of(2, 2, BEND)
    k = held_since_before(E)
    assert guided(k, g, (1, 0), (0, 0), stops=((1, 0),)) is None


def test_nothing_held_stops_in_a_corridor():
    g = grid_of(2, 2, BEND)
    assert guided(KeyboardSteer(), g, (1, 0), (0, 0)) is None


def test_forget_position_clears_pause_and_stop_but_not_held_keys():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    assert guided(k, g, (1, 1), (0, 1)) is None  # starts the pause at the fork
    k.forget_position()
    assert k.held == [E]
    # the pause, stop and last-cell tracking were reset, so this is a fresh fork
    # visit rather than a continuation of the one before forget_position().
    assert guided(k, g, (1, 1), (0, 1)) is None
    k.tick(1.0)
    assert guided(k, g, (1, 1), (0, 1)) == (2, 1)


def test_zero_pause_does_not_cost_a_frame_at_a_fork():
    g = grid_of(3, 3, CROSS)
    k = held_since_before(E)
    assert k.choose(g, (1, 1), (0, 1), True, (), FAR, 0, 0.0) == (2, 1)


def test_is_reverse():
    assert is_reverse((0, 0), (1, 0), W)
    assert not is_reverse((0, 0), (1, 0), E)
    assert not is_reverse((0, 0), None, W)


def test_steer_moves_to_the_neighbor_closest_to_the_cursor():
    assert steer_toward(fork_grid(), (1, 0), (2.9, 0.5)) == (2, 0)


def test_steer_stays_when_the_cursor_is_in_the_cell():
    assert steer_toward(fork_grid(), (1, 0), (1.2, 0.8)) is None


def test_steer_stays_when_a_wall_blocks_every_closer_way():
    assert steer_toward(fork_grid(), (0, 1), (1.5, 1.5)) is None


def test_dash_path_follows_a_straight_open_run():
    assert dash_path(fork_grid(), (0, 0), (2, 0)) == [(1, 0), (2, 0)]


def test_dash_path_rejects_walls_diagonals_self_and_outside():
    g = fork_grid()
    assert dash_path(g, (0, 1), (2, 1)) is None
    assert dash_path(g, (0, 0), (1, 1)) is None
    assert dash_path(g, (0, 0), (0, 0)) is None
    assert dash_path(g, (0, 0), (5, 0)) is None


def test_path_steer_follows_then_finishes():
    p = PathSteer([(1, 0), (2, 0)])
    assert p.choose((0, 0)) == (1, 0)
    assert p.choose((1, 0)) == (2, 0)
    assert p.done and p.choose((2, 0)) is None


def test_path_steer_gives_up_when_not_adjacent():
    p = PathSteer([(2, 0)])
    assert p.choose((0, 0)) is None and p.done


def test_auto_steer_walks_open_passages_to_the_end():
    g = fork_grid()
    a = AutoSteer(g, (2, 1), random.Random(1), 4)
    cell = (0, 1)
    for _ in range(100):
        nxt = a.choose(cell)
        if nxt is None:
            break
        assert nxt in g.open_neighbors(cell)
        cell = nxt
    assert cell == (2, 1) and a.done
