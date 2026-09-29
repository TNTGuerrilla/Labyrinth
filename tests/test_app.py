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


def test_stage_draws_the_notice_on_the_primary_board():
    import random
    from types import SimpleNamespace

    import pygame

    from maze_saver.app import Stage, make_slots
    from maze_saver.config import Settings
    from maze_saver.layout import Rect

    pygame.init()
    try:
        surface = pygame.Surface((800, 600))
        slot = make_slots(surface, [Rect(0, 0, 800, 600)], Settings(), random.Random(1),
                          False)[0]
        flips = []
        slot.window = SimpleNamespace(flip=lambda: flips.append(1))
        stage = Stage([slot], 60)
        stage.show_notice("Labyrinth Screensaver 9.9.9 is available.", 0.0)
        stage.frame(1 / 60, now=1.0)
        assert stage.watermark.corner == 0 and flips
    finally:
        pygame.quit()


def test_the_section_shrinks_the_primary_maze_until_it_fades():
    from types import SimpleNamespace

    from maze_saver.whats_new import SectionClock
    from maze_saver.whats_new_view import WhatsNewSection

    surface = pygame.Surface((1600, 900))
    quick = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500,
                     hold_seconds=0.5)
    slot = make_slots(surface, [Rect(0, 0, 1600, 900)], quick, random.Random(2), False)[0]
    slot.window = SimpleNamespace(flip=lambda: None)
    stage = Stage([slot], 60)
    section = WhatsNewSection("Labyrinth Screensaver updated to 9.9.9", [],
                              SectionClock(0.0), (1600, 900))
    seen = []
    stage.show_section(section, lambda: seen.append(True))
    stage.show_notice("Labyrinth Screensaver 9.9.10 is available.", 0.0)
    board = slot.board
    t = 0.0

    def step():
        nonlocal t
        t += 1 / 60
        stage.frame(1 / 60, now=t)

    while board.geometry is None:
        step()
    g = board.geometry
    assert g.x + g.width <= section.split.board.right
    mark = stage.watermark.rect_for(stage.watermark.corner, section.split.board)
    assert mark.right <= section.split.board.right
    while not seen:  # a minute, then the next solve, then the fade
        step()
    assert t >= 60 and stage.section is None
    while board.phase is not Phase.BLACK:  # the first maze to start after the fade
        step()
    while board.geometry is None:
        step()
    assert abs(board.geometry.x + board.geometry.width / 2 - 800) <= board.geometry.cell


def test_the_watermark_follows_the_area_of_the_maze_on_screen():
    from types import SimpleNamespace

    from maze_saver.whats_new import SectionClock
    from maze_saver.whats_new_view import WhatsNewSection

    surface = pygame.Surface((1600, 900))
    quick = Settings(min_cells=4, max_cells=6, gen_speed=1000, solve_speed=500,
                     hold_seconds=3.0)  # a hold longer than the fade
    slot = make_slots(surface, [Rect(0, 0, 1600, 900)], quick, random.Random(5), False)[0]
    slot.window = SimpleNamespace(flip=lambda: None)
    stage = Stage([slot], 60)
    section = WhatsNewSection("Labyrinth Screensaver updated to 9.9.9", [],
                              SectionClock(0.0), (1600, 900))
    seen = []
    stage.show_section(section, lambda: seen.append(True))
    stage.show_notice("Labyrinth Screensaver 9.9.10 is available.", 0.0)
    board = slot.board
    split = section.split.board
    t = 0.0

    def step():
        nonlocal t
        t += 1 / 60
        stage.frame(1 / 60, now=t)

    step()  # the section appears while the board is still black
    assert board.geometry is None and stage.watermark.area == split
    while not seen:
        step()
    # Faded while the maze laid out beside the section is still held on screen: the
    # watermark stays in that maze's area.
    assert board.phase is Phase.HOLD and board.area is None
    step()
    assert stage.watermark.area == split
    while board.geometry is None or board.phase is Phase.HOLD:
        step()
    assert board.maze_area is None and stage.watermark.area is None


def test_the_watermark_waits_for_a_maze_laid_out_with_the_notice_cap():
    from types import SimpleNamespace

    from maze_saver.board import NOTICE_COVERAGE

    surface = pygame.Surface((1600, 900))
    quick = Settings(min_cells=12, max_cells=12, gen_speed=1000, solve_speed=500,
                     hold_seconds=0.5, coverage=100)
    slot = make_slots(surface, [Rect(0, 0, 1600, 900)], quick, random.Random(3), False)[0]
    slot.window = SimpleNamespace(flip=lambda: None)
    stage = Stage([slot], 60)
    board = slot.board
    t = 0.0

    def step():
        nonlocal t
        t += 1 / 60
        stage.frame(1 / 60, now=t)

    while board.geometry is None:
        step()
    stage.show_notice("Labyrinth Screensaver 9.9.10 is available.", t)
    # The full-size maze on screen was laid out without the cap: no watermark over it.
    while board.geometry is not None:
        assert board.maze_notice is False and stage.watermark.corner is None
        step()
    step()  # black between mazes: the watermark shows
    assert stage.watermark.corner is not None
    while board.geometry is None:
        step()
    assert board.maze_notice is True
    assert board.geometry.height <= 900 * NOTICE_COVERAGE // 100
    assert stage.watermark.corner is not None


def test_startup_monitors_waits_for_monitors_to_appear():
    from maze_saver.app import startup_monitors
    from maze_saver.layout import Monitor
    real = [Monitor(0, 0, 1920, 1080)]
    answers = [[], [], real]
    sleeps = []
    found = startup_monitors(lambda: answers.pop(0), lambda: (0, 0, 800, 600, 0),
                             sleeps.append)
    assert found == real
    assert len(sleeps) == 2


def test_startup_monitors_falls_back_to_the_virtual_screen():
    from maze_saver.app import STARTUP_MONITOR_TRIES, STARTUP_MONITOR_WAIT, startup_monitors
    from maze_saver.layout import Monitor
    calls, sleeps = [], []

    def none():
        calls.append(1)
        return []

    found = startup_monitors(none, lambda: (-1920, 0, 3840, 1080, 2), sleeps.append)
    assert found == [Monitor(-1920, 0, 3840, 1080)]
    assert len(calls) == STARTUP_MONITOR_TRIES
    assert len(sleeps) == STARTUP_MONITOR_TRIES - 1
    assert 1.0 <= sum(sleeps) <= 3.0  # about two seconds in all
    assert sleeps == [STARTUP_MONITOR_WAIT] * (STARTUP_MONITOR_TRIES - 1)


def test_startup_monitors_without_a_virtual_screen_uses_the_desktop_size(monkeypatch):
    from maze_saver import app
    from maze_saver.layout import Monitor
    monkeypatch.setattr(app.pygame.display, "get_desktop_sizes", lambda: [(1280, 720)])
    found = app.startup_monitors(lambda: [], lambda: (0, 0, 0, 0, 0), lambda s: None)
    assert found == [Monitor(0, 0, 1280, 720)]
    monkeypatch.setattr(app.pygame.display, "get_desktop_sizes", lambda: [])
    found = app.startup_monitors(lambda: [], lambda: (0, 0, 0, 0, 0), lambda s: None)
    assert found == [Monitor(0, 0, *app.FALLBACK_SCREEN)]
