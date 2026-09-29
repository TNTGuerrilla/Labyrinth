import random

from maze_saver.board import BLACK_SECONDS, WELD_FLASH_SECONDS, Board, Phase
from maze_saver.config import Settings
from maze_saver.maze import edge_key
from tests.mazeutil import assert_perfect, bfs_path

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


def test_forced_leads_sets_head_count():
    settings = Settings(min_cells=20, max_cells=20, gen_speed=1000, solve_speed=500,
                        hold_seconds=0.5)
    b = Board(800, 600, settings, random.Random(1), forced_leads=6)
    run_until(b, Phase.DOTS)
    assert len(b.hues) == 6


def test_growth_speed_is_per_lead_not_shared():
    settings = Settings(min_cells=20, max_cells=20, gen_speed=10, solve_speed=500,
                        hold_seconds=0.5)
    solo = Board(800, 600, settings, random.Random(1), forced_leads=1)
    swarm = Board(800, 600, settings, random.Random(1), forced_leads=4)
    for b in (solo, swarm):
        while b.phase is not Phase.GENERATE:
            b.update(0.01)
    solo.update(0.5)
    swarm.update(0.5)
    assert len(solo.region_of) <= 6
    assert len(swarm.region_of) >= 14


def test_multi_lead_reaches_solve_with_perfect_maze():
    settings = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500,
                        hold_seconds=0.5)
    b = Board(400, 300, settings, random.Random(7), forced_leads=4)
    run_until(b, Phase.SOLVE)
    assert_perfect(b.grid)


def test_lookahead_zero_still_completes_solve():
    settings = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500,
                        hold_seconds=0.5, lookahead=0)
    b = Board(400, 300, settings, random.Random(8))
    run_until(b, Phase.HOLD)
    assert b.solved


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


def test_dot_glides_between_steps():
    slow = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=10, hold_seconds=0.5)
    b = Board(400, 300, slow, random.Random(9))
    run_until(b, Phase.SOLVE)
    assert b.glide_from is None and b.glide_progress == 1.0
    while b.glide_from is None:
        b.update(DT)
    first = b.glide_progress
    ch = b.update(DT)  # no new step at 10 steps per second, but the glide moves on
    assert b.glide_progress > first
    assert {b.glide_from, b.dot} <= ch.cells
    assert b.grid.is_open(b.glide_from, b.dot)


def test_glide_ends_when_solved():
    b = Board(400, 300, FAST, random.Random(10))
    run_until(b, Phase.HOLD)
    assert b.glide_from is None and b.glide_progress == 1.0 and b.dot == b.end


def centre_x(g):
    return g.x + g.width / 2


def test_area_applies_from_the_next_maze():
    board = Board(1000, 600, FAST, random.Random(3))
    board.set_area((0, 0, 700, 600))
    run_until(board, Phase.DOTS)
    g = board.geometry
    assert g.x + g.width <= 700 and abs(centre_x(g) - 350) <= g.cell
    board.set_area(None)
    assert board.geometry == g  # the maze on screen keeps its place
    run_until(board, Phase.BLACK)
    run_until(board, Phase.DOTS)
    assert abs(centre_x(board.geometry) - 500) <= board.geometry.cell


def test_area_offsets_the_maze():
    board = Board(600, 1000, FAST, random.Random(4))
    board.set_area((0, 0, 600, 700))
    run_until(board, Phase.DOTS)
    assert board.geometry.y + board.geometry.height <= 700
    board = Board(1000, 600, FAST, random.Random(4))
    board.set_area((200, 100, 600, 400))
    run_until(board, Phase.DOTS)
    g = board.geometry
    assert 200 <= g.x and g.x + g.width <= 800 and 100 <= g.y and g.y + g.height <= 500


def test_mazes_solved_counts_hold_entries():
    board = Board(400, 300, FAST, random.Random(1))
    assert board.mazes_solved == 0
    run_until(board, Phase.HOLD)
    assert board.mazes_solved == 1
    run_until(board, Phase.BLACK)
    run_until(board, Phase.HOLD)
    assert board.mazes_solved == 2


def test_maze_area_is_the_area_the_maze_on_screen_used():
    board = Board(1000, 600, FAST, random.Random(3))
    assert board.maze_area is None
    board.set_area((0, 0, 700, 600))
    assert board.maze_area is None  # nothing laid out yet
    run_until(board, Phase.DOTS)
    assert board.maze_area == (0, 0, 700, 600)
    board.set_area(None)
    assert board.maze_area == (0, 0, 700, 600)  # the maze on screen keeps its place
    run_until(board, Phase.BLACK)
    run_until(board, Phase.DOTS)
    assert board.maze_area is None


def _within(board, coverage):
    g = board.geometry
    return (min(g.width, g.height) <= min(board.width, board.height) * coverage // 100
            and max(g.width, g.height) <= max(board.width, board.height) * coverage // 100)


def test_coverage_setting_sizes_the_maze():
    b = Board(1600, 900, Settings(min_cells=12, max_cells=12, coverage=50), random.Random(4))
    run_until(b, Phase.DOTS)
    assert b.geometry.height == 900 * 50 // 100 // 12 * 12 and _within(b, 50)


def test_the_notice_caps_coverage_from_the_next_maze():
    from maze_saver.board import NOTICE_COVERAGE
    assert NOTICE_COVERAGE == 85
    settings = Settings(min_cells=12, max_cells=12, gen_speed=1000, solve_speed=500,
                        hold_seconds=0.5, coverage=100)
    b = Board(1600, 900, settings, random.Random(6))
    run_until(b, Phase.DOTS)
    assert b.maze_notice is False and b.geometry.height == 900 // 12 * 12
    b.set_notice(True)
    assert b.maze_notice is False  # the maze on screen was laid out without the cap
    run_until(b, Phase.BLACK)
    assert b.maze_notice is False
    run_until(b, Phase.DOTS)
    assert b.maze_notice is True
    assert b.geometry.height == 900 * 85 // 100 // 12 * 12 and _within(b, 85)


def test_the_notice_leaves_a_smaller_coverage_alone():
    b = Board(1600, 900, Settings(min_cells=12, max_cells=12, coverage=60), random.Random(7))
    b.set_notice(True)
    run_until(b, Phase.DOTS)
    assert b.maze_notice is True and b.geometry.height == 900 * 60 // 100 // 12 * 12
