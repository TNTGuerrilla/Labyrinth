import pytest

from maze_game.trail import Trail


def walked(*cells):
    t = Trail(cells[0])
    for a, b in zip(cells, cells[1:]):
        t.move(a, b)
    return t


def test_forward_moves_are_bright():
    t = walked((0, 0), (1, 0), (2, 0))
    assert t.route == [(0, 0), (1, 0), (2, 0)]
    assert t.edges == {((0, 0), (1, 0)): True, ((1, 0), (2, 0)): True}


def test_backing_up_dims_the_edge_left_behind():
    t = walked((0, 0), (1, 0), (2, 0), (1, 0))
    assert t.cell == (1, 0)
    assert t.edges[((1, 0), (2, 0))] is False
    assert t.edges[((0, 0), (1, 0))] is True


def test_walking_a_dim_edge_again_brightens_it():
    t = walked((0, 0), (1, 0), (0, 0), (1, 0))
    assert t.edges[((0, 0), (1, 0))] is True


def test_move_must_start_at_the_current_cell():
    with pytest.raises(ValueError):
        Trail((0, 0)).move((1, 0), (2, 0))
