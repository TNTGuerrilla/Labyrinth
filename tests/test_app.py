import random
import sys

import pygame
import pytest

if sys.platform != "win32":
    pytest.skip("Windows only", allow_module_level=True)

from maze_saver.app import Stage, make_slots, needs_rebuild  # noqa: E402
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


def test_stage_dirty_rects_stay_inside_their_slot(monkeypatch):
    surface = pygame.display.set_mode((900, 400))
    rects = [Rect(0, 0, 400, 300), Rect(450, 100, 400, 300)]
    slots = make_slots(surface, rects, FAST, random.Random(7), first_cycle=False)
    stage = Stage(slots, 60)
    slot_rects = [pygame.Rect(r.x, r.y, r.w, r.h) for r in rects]
    recorded = []
    monkeypatch.setattr(pygame.display, "update", lambda dirty: recorded.extend(dirty))
    for _ in range(120):
        stage.frame(1 / 60)
    assert recorded
    assert all(any(slot_rect.contains(r) for slot_rect in slot_rects) for r in recorded)
    assert any(slot_rects[0].contains(r) for r in recorded)
    assert any(slot_rects[1].contains(r) for r in recorded)
    stage.close()


def test_needs_rebuild_true_only_when_signature_differs():
    assert needs_rebuild((0, 0, 1920, 1080, 1), (0, 0, 1920, 1080, 1)) is False
    assert needs_rebuild((0, 0, 1920, 1080, 1), (0, 0, 2560, 1080, 2)) is True
    assert needs_rebuild((0, 0, 1920, 1080, 1), (-1920, 0, 3840, 1080, 2)) is True
