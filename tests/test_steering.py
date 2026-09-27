import random

from maze_saver.maze import E, N, S, W
from maze_game.steering import (AutoSteer, KeyboardSteer, PathSteer, dash_path, is_reverse,
                                steer_toward)
from tests.gameutil import fork_grid


def held(*dirs):
    k = KeyboardSteer()
    for d in dirs:
        k.press(d)
    return k


def test_keyboard_goes_where_held():
    assert held(E).choose(fork_grid(), (0, 0), None, True, ()) == (1, 0)


def test_nothing_held_stays():
    assert KeyboardSteer().choose(fork_grid(), (0, 0), None, True, ()) is None


def test_latest_press_wins_and_release_falls_back():
    k = held(E, S)
    assert k.wanted == S
    k.release(S)
    assert k.wanted == E
    k.clear()
    assert k.wanted is None


def test_follow_bends_takes_the_other_corridor_exit():
    assert held(W).choose(fork_grid(), (0, 0), (1, 0), True, ()) == (0, 1)


def test_follow_bends_off_stops_at_the_bend():
    assert held(W).choose(fork_grid(), (0, 0), (1, 0), False, ()) is None


def test_bends_are_not_followed_at_forks_stops_or_from_rest():
    g = fork_grid()
    assert held(N).choose(g, (1, 0), (0, 0), True, ()) is None
    assert held(W).choose(g, (0, 0), (1, 0), True, ((0, 0),)) is None
    assert held(W).choose(g, (0, 0), None, True, ()) is None


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
