import pygame
import pytest

from labyrinth_update.notes import ITEM, TEXT, NoteLine
from maze_game.ui.whats_new_dialog import WhatsNewDialog

LONG = [NoteLine(ITEM, f"Change number {i} with some words to wrap") for i in range(80)]


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def test_short_notes_do_not_scroll():
    d = WhatsNewDialog("Labyrinth updated to 1.2.0", [NoteLine(TEXT, "Faster")])
    d.draw(pygame.Surface((1280, 720)))
    assert d.handle("down") is None and d.scroll == 0


def test_arrows_and_wheel_scroll_within_bounds():
    d = WhatsNewDialog("Labyrinth updated to 1.2.0", LONG)
    d.draw(pygame.Surface((1280, 720)))
    d.handle("down")
    assert d.scroll == 1
    d.wheel(-1)
    assert d.scroll == 4
    d.handle("up")
    assert d.scroll == 3
    for _ in range(500):
        d.handle("down")
    bottom = d.scroll
    d.draw(pygame.Surface((1280, 720)))
    assert d.scroll == bottom > 0
    d.wheel(100)
    assert d.scroll == 0


def test_enter_esc_and_ok_close_it():
    d = WhatsNewDialog("Labyrinth updated to 1.2.0", LONG)
    d.draw(pygame.Surface((1280, 720)))
    assert d.handle("confirm") == "close" and d.handle("cancel") == "close"
    assert d.click(d.hits.rect_for("ok").center) == "close"
    assert d.click((1, 1)) is None
