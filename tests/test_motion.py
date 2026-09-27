import pytest

from maze_game.motion import Mover


def east(cell, came_from):
    return (cell[0] + 1, cell[1]) if cell[0] < 3 else None


def stay(cell, came_from):
    return None


def test_rests_until_the_chooser_moves():
    m = Mover((0, 0))
    assert m.advance(1.0, stay) == []
    assert not m.moving and m.position() == (0.5, 0.5)


def test_glides_and_switches_cell_at_the_midpoint():
    m = Mover((0, 0))
    assert m.advance(0.4, east) == []
    assert m.cell == (0, 0) and m.position() == pytest.approx((0.9, 0.5))
    assert m.advance(0.2, east) == [((0, 0), (1, 0))]
    assert m.cell == (1, 0)


def test_long_advance_crosses_several_cells_then_stops():
    m = Mover((0, 0))
    assert m.advance(10.0, east) == [((0, 0), (1, 0)), ((1, 0), (2, 0)), ((2, 0), (3, 0))]
    assert m.frm == (3, 0) and not m.moving


def test_chooser_sees_where_the_dot_came_from():
    calls = []

    def choose(cell, came_from):
        calls.append((cell, came_from))
        return (1, 0) if cell == (0, 0) else None

    m = Mover((0, 0))
    m.advance(2.0, choose)
    assert calls == [((0, 0), None), ((1, 0), (0, 0))]
    assert m.frm == (1, 0) and not m.moving


def test_letting_go_mid_glide_finishes_at_the_next_center():
    m = Mover((0, 0))
    m.advance(0.3, east)
    assert m.advance(1.0, stay) == [((0, 0), (1, 0))]
    assert m.frm == (1, 0) and not m.moving


def test_reverse_before_the_midpoint_keeps_the_cell():
    m = Mover((0, 0))
    m.advance(0.3, east)
    m.reverse()
    assert m.cell == (0, 0) and m.frm == (1, 0) and m.to == (0, 0)
    assert m.advance(1.0, stay) == []
    assert m.frm == (0, 0)


def test_reverse_after_the_midpoint_moves_back():
    m = Mover((0, 0))
    m.advance(0.7, east)
    m.reverse()
    assert m.cell == (1, 0)
    assert m.advance(1.0, stay) == [((1, 0), (0, 0))]


def test_reverse_exactly_at_the_midpoint_keeps_the_cell():
    m = Mover((0, 0))
    m.advance(0.5, east)
    assert m.cell == (1, 0)
    m.reverse()
    assert m.cell == (1, 0)


def test_next_center_and_place():
    m = Mover((0, 0))
    m.advance(0.3, east)
    assert m.next_center == (1, 0)
    m.place((3, 3))
    assert m.cell == (3, 3) and not m.moving and m.came_from is None
