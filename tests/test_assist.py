from maze_game.assist import hint_cells, perfect_steps, route
from tests.gameutil import fork_grid


def test_route_and_perfect_steps():
    g = fork_grid()
    assert route(g, (0, 1), (1, 1)) == [(0, 1), (0, 0), (1, 0), (1, 1)]
    assert perfect_steps(g, (0, 1), (1, 1)) == 3


def test_route_to_itself():
    assert route(fork_grid(), (1, 0), (1, 0)) == [(1, 0)]


def test_hint_from_off_the_path_leads_back():
    assert hint_cells(fork_grid(), (2, 1), (0, 1), 2) == [(2, 0), (1, 0)]


def test_hint_stops_at_the_end():
    assert hint_cells(fork_grid(), (0, 1), (2, 1), 8) == [(0, 0), (1, 0), (2, 0), (2, 1)]
