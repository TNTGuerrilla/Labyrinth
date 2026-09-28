from types import SimpleNamespace

import pygame
import pytest

from maze_game.keymap import Keymap
from maze_game.ui.toolbar import TOOLBAR_H, Toolbar, ToolbarState
from maze_game.ui.widgets import ACTIVE, BORDER, HOVER, Hits, button_rect, format_time
from maze_game.ui.win_screen import WinScreen, win_lines


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def result(**kw):
    values = dict(steps=40, perfect=30, efficiency=75, elapsed=65.0, hints=2, assisted=False,
                  auto_steps=0)
    values.update(kw)
    return SimpleNamespace(**values)


def test_format_time():
    assert format_time(0) == "0:00"
    assert format_time(75.9) == "1:15"
    assert format_time(3600) == "60:00"


def test_hits_returns_the_first_match():
    hits = Hits()
    hits.add(pygame.Rect(0, 0, 10, 10), "a")
    hits.add(pygame.Rect(0, 0, 20, 20), "b")
    assert hits.at((5, 5)) == "a" and hits.at((15, 15)) == "b" and hits.at((50, 50)) is None
    assert hits.rect_for("b") == pygame.Rect(0, 0, 20, 20)


def test_toolbar_hit_testing():
    surface = pygame.Surface((1400, 700))
    toolbar = Toolbar()
    toolbar.draw(surface, Keymap(), ToolbarState("medium", False, True, 3, 12.0), (-1, -1))
    for action in ("new", "replay", "hint", "autosolve", "flash", "small", "medium", "large",
                   "xl", "custom", "colors", "settings"):
        rect = toolbar.hits.rect_for(action)
        assert rect.bottom <= TOOLBAR_H
        assert toolbar.action_at(rect.center) == action
    assert toolbar.action_at((5, 300)) is None


def test_toolbar_tooltip_draws_below_the_bar():
    surface = pygame.Surface((1400, 700))
    toolbar = Toolbar()
    state = ToolbarState("medium", True, False, 0, 0.0)
    toolbar.draw(surface, Keymap(), state, (-1, -1))
    spot = toolbar.hits.rect_for("hint").center
    surface.fill((0, 0, 0))
    toolbar.draw(surface, Keymap(), state, spot)
    assert tuple(surface.get_at((spot[0] + 4, TOOLBAR_H + 12)))[:3] != (0, 0, 0)


def test_win_lines():
    assert win_lines(result()) == [("Steps", "40"), ("Perfect", "30"), ("Efficiency", "75%"),
                                   ("Time", "1:05"), ("Hints used", "2")]
    assert win_lines(result(assisted=True, auto_steps=12))[-1] == ("Auto-solve steps", "12")


def test_win_screen_buttons():
    surface = pygame.Surface((1000, 700))
    screen = WinScreen()
    screen.draw(surface, pygame.Rect(0, 40, 1000, 660), result(assisted=True, auto_steps=3),
                Keymap())
    assert screen.click(screen.hits.rect_for("replay").center) == "replay"
    assert screen.click(screen.hits.rect_for("new").center) == "new"
    assert screen.click((1, 1)) is None


def update_state(**kw):
    values = dict(update_label="Update to 1.2.0", update_short="Update",
                  update_tip="Labyrinth 1.2.0 is available.", update_dismiss=True)
    values.update(kw)
    return ToolbarState("medium", False, True, 3, 12.0, **values)


@pytest.mark.parametrize("width", [960, 1280, 1920])
def test_update_control_is_one_split_button_left_of_the_counters(width):
    surface = pygame.Surface((width, 700))
    toolbar = Toolbar()
    toolbar.draw(surface, Keymap(), update_state(), (-1, -1))
    update = toolbar.hits.rect_for("update")
    close = toolbar.hits.rect_for("update_dismiss")
    settings = toolbar.hits.rect_for("settings")
    assert settings.right < update.left and update.right == close.left
    assert (update.top, update.h) == (close.top, close.h)
    assert close.right <= width - 12
    assert toolbar.action_at(update.center) == "update"
    assert toolbar.action_at(close.center) == "update_dismiss"


def test_hover_highlights_only_the_part_under_the_mouse():
    surface = pygame.Surface((1400, 700))
    toolbar = Toolbar()
    toolbar.draw(surface, Keymap(), update_state(), (-1, -1))
    update = toolbar.hits.rect_for("update")
    close = toolbar.hits.rect_for("update_dismiss")

    def color(x, y):
        return tuple(surface.get_at((x, y)))[:3]

    assert color(close.x, close.centery) == BORDER  # the divider
    toolbar.draw(surface, Keymap(), update_state(), close.center)
    assert color(update.x + 4, update.centery) == ACTIVE
    assert color(close.right - 4, close.centery) == HOVER
    toolbar.draw(surface, Keymap(), update_state(), update.center)
    assert color(update.x + 4, update.centery) == HOVER
    assert color(close.right - 4, close.centery) == ACTIVE


def test_wide_windows_get_the_full_label():
    surface = pygame.Surface((1920, 700))
    toolbar = Toolbar()
    toolbar.draw(surface, Keymap(), update_state(), (-1, -1))
    full = button_rect("Update to 1.2.0", (0, 0), size=15)
    assert toolbar.hits.rect_for("update").w == full.w


def test_no_update_means_no_update_buttons():
    surface = pygame.Surface((1400, 700))
    toolbar = Toolbar()
    toolbar.draw(surface, Keymap(), ToolbarState("medium", False, True, 3, 12.0), (-1, -1))
    assert toolbar.hits.rect_for("update") is None
    assert toolbar.hits.rect_for("update_dismiss") is None


def test_update_without_dismiss():
    surface = pygame.Surface((1400, 700))
    toolbar = Toolbar()
    toolbar.draw(surface, Keymap(), update_state(update_dismiss=False), (-1, -1))
    assert toolbar.hits.rect_for("update") is not None
    assert toolbar.hits.rect_for("update_dismiss") is None


def test_update_tooltip_draws_below_the_bar():
    surface = pygame.Surface((1400, 700))
    toolbar = Toolbar()
    state = update_state()
    toolbar.draw(surface, Keymap(), state, (-1, -1))
    spot = toolbar.hits.rect_for("update").center
    surface.fill((0, 0, 0))
    toolbar.draw(surface, Keymap(), state, spot)
    assert tuple(surface.get_at((min(spot[0] + 4, 1390), TOOLBAR_H + 12)))[:3] != (0, 0, 0)
