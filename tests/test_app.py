import random
import sys

import pygame
import pytest

if sys.platform != "win32":
    pytest.skip("Windows only", allow_module_level=True)

from maze_saver.app import Stage, make_slots  # noqa: E402
from maze_saver.board import Phase  # noqa: E402
from maze_saver.config import Settings  # noqa: E402
from maze_saver.layout import Rect  # noqa: E402

# Long hold so no board can cycle back to BLACK within the 4 simulated seconds.
FAST = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500, hold_seconds=10)


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def any_lit(surface, rect):
    return any(tuple(surface.get_at((x, y)))[:3] != (0, 0, 0)
               for x in range(rect.x, rect.right, 3) for y in range(rect.y, rect.bottom, 3))


def test_stage_draws_every_board_in_its_own_area():
    surface = pygame.display.set_mode((800, 300))
    rects = [Rect(0, 0, 400, 300), Rect(400, 0, 400, 300)]
    slots = make_slots(surface, rects, FAST, random.Random(5), first_cycle=False)
    stage = Stage(slots, 60)
    for _ in range(240):
        stage.frame(1 / 60)
    assert all(slot.board.phase is not Phase.BLACK for slot in slots)
    assert any_lit(surface, pygame.Rect(0, 0, 400, 300))
    assert any_lit(surface, pygame.Rect(400, 0, 400, 300))
    stage.close()
