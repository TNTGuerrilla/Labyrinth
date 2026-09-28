import pygame
import pytest

from labyrinth_update.notes import ITEM, TEXT, NoteLine
from maze_saver.whats_new import SectionClock
from maze_saver.whats_new_view import WhatsNewSection

SIZE = (1920, 1080)


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def lit(surface, rect):
    return any(tuple(surface.get_at((x, y)))[:3] != (0, 0, 0)
               for x in range(rect.x, rect.right, 3) for y in range(rect.y, rect.bottom, 3))


def section(lines, clock=None):
    return WhatsNewSection("Labyrinth Screensaver updated to 9.9.9", lines,
                           clock or SectionClock(0.0), SIZE)


def test_section_draws_in_its_box_and_redraws_only_the_footer_each_second():
    surface = pygame.Surface(SIZE)
    s = section([NoteLine(TEXT, "Faster")])
    assert s.update(surface, 0.0, False) == [s.rect]
    b = s.split.board
    assert lit(surface, s.rect) and not lit(surface, pygame.Rect(b.x, b.y, b.w, b.h))
    assert s.update(surface, 0.5, False) == []
    footer = s.update(surface, 1.0, False)
    assert len(footer) == 1 and s.rect.contains(footer[0]) and footer[0].h < s.rect.h // 4
    assert s.update(surface, 1.0, True) == [s.rect]  # the board cleared the surface


def test_long_notes_end_with_the_more_line():
    many = [NoteLine(ITEM, f"Change number {i}") for i in range(200)]
    s = section(many)
    assert len(s.shown_lines) < len(many)
    tail = " ".join(line.text for line in s.shown_lines[-2:])
    assert tail.endswith("github.com/TNTGuerrilla/Labyrinth/releases")


def test_fading_out_erases_the_section():
    surface = pygame.Surface(SIZE)
    clock = SectionClock(0.0)
    s = section([NoteLine(TEXT, "Faster")], clock)
    s.update(surface, 61.0, False)
    clock.board_solved(61.0)
    assert s.update(surface, 61.5, False) == [s.rect]  # every frame while fading
    s.update(surface, 62.5, False)
    assert not lit(surface, s.rect)
