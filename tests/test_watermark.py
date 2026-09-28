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
