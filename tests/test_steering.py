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


def test_start_and_finish_stop_the_dot():
    g = grid_of(2, 2, BEND)
    k = held_since_before(E)
    assert guided(k, g, (1, 0), (0, 0), stops=((1, 0),)) is None


def test_nothing_held_stops_in_a_corridor():
    g = grid_of(2, 2, BEND)
    assert guided(KeyboardSteer(), g, (1, 0), (0, 0)) is None


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
