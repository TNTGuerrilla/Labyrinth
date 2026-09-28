import pygame
import pytest

from maze_saver.layout import Rect
from maze_saver.watermark import CORNER_SECONDS, Watermark, primary_index

MESSAGE = ("Labyrinth Screensaver 9.9.9 is available. "
           "Open Screen Saver Settings to update.")


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def test_primary_index():
    assert primary_index([Rect(-1920, 0, 1920, 1080), Rect(0, 0, 2560, 1440)]) == 1
    assert primary_index([Rect(100, 0, 800, 600)]) == 0


@pytest.mark.parametrize("size", [(1920, 1080), (1080, 1920), (800, 600), (3840, 2160)])
def test_watermark_stays_in_the_margin_the_maze_never_uses(size):
    w, h = size
    mark = Watermark(MESSAGE, size, 0.0)
    for corner in range(4):
        r = mark.rect_for(corner)
        assert 0 <= r.left and r.right <= w
        assert r.bottom <= h // 10 or r.top >= h - h // 10


def test_watermark_draws_moves_and_erases():
    surface = pygame.Surface((1920, 1080))
    mark = Watermark(MESSAGE, (1920, 1080), 0.0)
    first = mark.update(surface, 1.0, False)
    assert len(first) == 1
    assert mark.update(surface, 2.0, False) == []
    assert len(mark.update(surface, 2.0, True)) == 1
    moved = mark.update(surface, CORNER_SECONDS + 1, False)
    assert len(moved) == 2
    assert tuple(pygame.transform.average_color(surface, first[0]))[:3] == (0, 0, 0)


def test_watermark_keeps_to_the_given_area():
    area = Rect(0, 0, 1344, 1080)  # the board's part of a 1920 x 1080 monitor
    mark = Watermark(MESSAGE, (1920, 1080), 0.0)
    for corner in range(4):
        r = mark.rect_for(corner, area)
        assert 0 <= r.left and r.right <= area.right
        assert r.bottom <= 1080 // 10 or r.top >= 1080 - 1080 // 10


def test_watermark_moves_when_its_area_changes():
    surface = pygame.Surface((1920, 1080))
    mark = Watermark(MESSAGE, (1920, 1080), 0.0)
    small = Rect(0, 0, 1344, 1080)
    first = mark.update(surface, 1.0, False, small)
    assert mark.update(surface, 2.0, False, small) == []
    moved = mark.update(surface, 3.0, False, None)
    assert len(moved) == 2 and moved[1].right > small.right
    # The new watermark can legitimately overlap the tail of the old rect (the message is
    # wider than the shift between the two anchors), so only the genuinely stale part (left
    # of the new rect) must be erased to black.
    stale = first[0].clip(pygame.Rect(0, 0, moved[1].left, surface.get_height()))
    assert stale.width > 0
    assert tuple(pygame.transform.average_color(surface, stale))[:3] == (0, 0, 0)
