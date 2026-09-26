import random

from maze_saver.board import BLACK_SECONDS, WELD_FLASH_SECONDS, Board, Phase
from maze_saver.config import Settings
from maze_saver.maze import edge_key
from tests.mazeutil import bfs_path

FAST = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500, hold_seconds=0.5)
DT = 1 / 60


def run_until(board, phase, limit=100000):
    changes = []
    for _ in range(limit):
        changes.append(board.update(DT))
        if board.phase is phase:
            return changes
    raise AssertionError(f"never reached {phase}")


def test_first_update_clears():
    b = Board(400, 300, FAST, random.Random(1))
    ch = b.update(0.01)
    assert ch.clear and b.phase is Phase.BLACK and b.geometry is None


def test_black_waits_then_shows_dots():
    b = Board(400, 300, FAST, random.Random(1))
    b.update(BLACK_SECONDS - 0.01)
    assert b.phase is Phase.BLACK
    ch = b.update(0.02)
    assert b.phase is Phase.DOTS
    assert ch.cells == {b.start, b.end}
    assert b.geometry is not None


def test_initial_delay_extends_black():
    b = Board(400, 300, FAST, random.Random(1), initial_delay=1.5)
    b.update(BLACK_SECONDS + 1.0)
    assert b.phase is Phase.BLACK
    b.update(0.6)
    assert b.phase is Phase.DOTS


def test_full_cycle_order():
    b = Board(400, 300, FAST, random.Random(2))
    seen = [b.phase]
    while not (seen[-1] is Phase.BLACK and Phase.HOLD in seen):
        b.update(DT)
        if b.phase is not seen[-1]:
            seen.append(b.phase)
    assert seen == [Phase.BLACK, Phase.DOTS, Phase.GENERATE, Phase.SOLVE, Phase.HOLD, Phase.BLACK]


def test_generation_builds_full_maze_with_regions():
    b = Board(400, 300, FAST, random.Random(3))
    run_until(b, Phase.SOLVE)
    g = b.grid
    assert g.passage_count() == g.cols * g.rows - 1
    assert len(b.region_of) == g.cols * g.rows
    assert all(r < len(b.hues) for r in b.region_of.values())
    assert b.heads == {}
    assert b.dot == b.start


def test_solve_leaves_true_path_bright():
    b = Board(400, 300, FAST, random.Random(4))
    run_until(b, Phase.HOLD)
    assert b.solved and b.dot == b.end
    path = bfs_path(b.grid, b.start, b.end)
    bright = {k for k, v in b.trail.items() if v}
    assert bright == {edge_key(path[i], path[i + 1]) for i in range(len(path) - 1)}


def test_changed_cells_are_on_the_board():
    b = Board(400, 300, FAST, random.Random(5))
    for ch in run_until(b, Phase.HOLD):
        for c in ch.cells:
            assert b.grid.in_bounds(c)


def test_hold_then_clears_and_resets():
    b = Board(400, 300, FAST, random.Random(6))
    run_until(b, Phase.HOLD)
    ch = b.update(FAST.hold_seconds + 0.01)
    assert b.phase is Phase.BLACK and ch.clear and not ch.cells
    assert b.geometry is None and b.trail == {} and b.dot is None


def test_welds_flash_then_expire():
    for seed in range(100):
        b = Board(400, 300, FAST, random.Random(seed))
        run_until(b, Phase.DOTS)
        if len(b.hues) > 1:
            break
    seen_weld = False
    while b.phase is not Phase.SOLVE:
        b.update(DT)
        seen_weld = seen_weld or bool(b.welds)
    assert seen_weld
    flashing = set(b.welds)
    ch = b.update(WELD_FLASH_SECONDS + 0.01)
    assert b.welds == {}
    for edge in flashing:
        assert set(edge) <= ch.cells
