from types import SimpleNamespace

import pygame
import pytest

from maze_game.keymap import Keymap
from maze_game.ui import toolbar as toolbar_module
from maze_game.ui.toolbar import TOOLBAR_H, Toolbar, ToolbarState
from maze_game.ui.widgets import (ACTIVE, BORDER, HOVER, Hits, button_rect, font,
                                  format_time)
from maze_game.ui.win_screen import WinScreen, win_lines


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def result(**kw):
    values = dict(explored=40, shortest=30, efficiency=75, elapsed=65.0, hints=2,
                  assisted=False, auto_explored=0)
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
    assert win_lines(result()) == [("Cells explored", "40"), ("Shortest route", "30"),
                                   ("Efficiency", "75%"), ("Time", "1:05"),
                                   ("Hints used", "2")]
    assert win_lines(result(assisted=True, auto_explored=12))[-1] == ("Auto-solved cells", "12")


def test_win_screen_buttons():
    surface = pygame.Surface((1000, 700))
    screen = WinScreen()
    screen.draw(surface, pygame.Rect(0, 40, 1000, 660), result(assisted=True, auto_explored=3),
                Keymap())
    assert screen.click(screen.hits.rect_for("replay").center) == "replay"
    assert screen.click(screen.hits.rect_for("new").center) == "new"
    assert screen.click((1, 1)) is None


def update_state(**kw):
    values = dict(update_label="Update to 1.2.0", update_short="Update",
                  update_tip="Labyrinth 1.2.0 is available.", update_dismiss=True)
    values.update(kw)
    return ToolbarState("medium", False, True, 3, 12.0, **values)


@pytest.mark.parametrize("width", [1280, 1920])
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


def drawn_texts(monkeypatch):
    """Collect every (string, position) the toolbar draws with its own text() calls."""
    seen = []
    real = toolbar_module.text
    monkeypatch.setattr(toolbar_module, "text",
                        lambda surface, string, pos, *a, **kw: (seen.append((string, pos)),
                                                                real(surface, string, pos, *a, **kw)))
    return seen


def stats_left(string, width):
    return width - 12 - font(15).size(string)[0]


@pytest.mark.parametrize("explored,elapsed", [(0, 0.0), (12345, 3723.0)])
def test_stats_never_overlap_the_buttons_without_an_update(monkeypatch, explored, elapsed):
    seen = drawn_texts(monkeypatch)
    for width in range(960, 1400, 20):
        seen.clear()
        toolbar = Toolbar()
        toolbar.draw(pygame.Surface((width, 700)), Keymap(),
                     ToolbarState("medium", False, True, explored, elapsed), (-1, -1))
        last = toolbar.hits.rect_for("settings").right
        assert all(stats_left(string, width) > last for string, _ in seen), width


def test_wide_window_still_shows_the_full_stats_without_an_update(monkeypatch):
    seen = drawn_texts(monkeypatch)
    Toolbar().draw(pygame.Surface((1600, 700)), Keymap(),
                   ToolbarState("medium", False, True, 12345, 3723.0), (-1, -1))
    assert [s for s, _ in seen] == ["Explored 12345     Time 62:03"]


def test_narrow_window_falls_back_to_compact_then_nothing(monkeypatch):
    seen = drawn_texts(monkeypatch)
    state = ToolbarState("medium", False, True, 12345, 3723.0)
    shown = set()
    for width in range(700, 1400, 10):
        seen.clear()
        Toolbar().draw(pygame.Surface((width, 700)), Keymap(), state, (-1, -1))
        shown.add(seen[0][0] if seen else None)
    assert shown == {None, "12345   62:03", "Explored 12345     Time 62:03"}


@pytest.mark.parametrize("width", [960, 1100, 1600])
def test_screensaver_shows_only_its_word_in_the_stats_area(monkeypatch, width):
    seen = drawn_texts(monkeypatch)
    for update in ({}, dict(update_label="Update to 1.2.0", update_short="Update",
                            update_dismiss=True)):
        seen.clear()
        toolbar = Toolbar()
        toolbar.draw(pygame.Surface((width, 700)), Keymap(),
                     ToolbarState("medium", False, True, 12345, 3723.0, screensaver=True,
                                  **update), (-1, -1))
        assert {s for s, _ in seen} <= {"Screensaver"}, (width, update)
        if width == 1600:
            assert [s for s, _ in seen] == ["Screensaver"]


def test_screensaver_compact_fallback_is_the_word_or_nothing(monkeypatch):
    seen = drawn_texts(monkeypatch)
    state = ToolbarState("medium", False, True, 1, 1.0, screensaver=True, update_label="Update",
                         update_short="Update")
    for width in range(700, 1400, 10):
        seen.clear()
        Toolbar().draw(pygame.Surface((width, 700)), Keymap(), state, (-1, -1))
        assert {s for s, _ in seen} <= {"Screensaver"}, width


def test_saver_button_tooltip_follows_the_mode(monkeypatch):
    seen = drawn_texts(monkeypatch)
    for running, tip in ((False, "Start screensaver (M)"),
                         (True, "Stop screensaver (Space or Esc)")):
        toolbar = Toolbar()
        surface = pygame.Surface((1400, 700))
        state = ToolbarState("medium", False, True, 0, 0.0, screensaver=running)
        toolbar.draw(surface, Keymap(), state, (-1, -1))
        seen.clear()
        toolbar.draw(surface, Keymap(), state, toolbar.hits.rect_for("screensaver").center)
        assert tip in [s for s, _ in seen]


UPDATE_KW = dict(update_label="Update to 1.2.0", update_short="Update", update_dismiss=True)


def test_toolbar_buttons_never_overlap_and_the_right_side_stays_clear(monkeypatch):
    seen = drawn_texts(monkeypatch)
    for kw in ({}, UPDATE_KW):
        for width in range(960, 1400, 20):
            seen.clear()
            toolbar = Toolbar()
            toolbar.draw(pygame.Surface((width, 700)), Keymap(),
                         ToolbarState("medium", False, True, 12345, 3723.0, **kw), (-1, -1))
            buttons = [r for r, a in toolbar.hits._items if a not in ("update", "update_dismiss")]
            for i, a in enumerate(buttons):
                assert all(not a.colliderect(b) for b in buttons[i + 1:]), (width, kw)
            last = max(r.right for r in buttons)
            assert all(stats_left(string, width) > last for string, _ in seen), (width, kw)
            for action in ("update", "update_dismiss"):
                rect = toolbar.hits.rect_for(action)
                if rect is not None:
                    assert rect.left > last and rect.right <= width - 12, (width, kw, action)
            assert (toolbar.hits.rect_for("update") is None) == (
                toolbar.hits.rect_for("update_dismiss") is None), (width, kw)


def test_update_control_is_hidden_when_even_the_short_form_does_not_fit():
    hidden = False
    for width in range(960, 1400, 20):
        toolbar = Toolbar()
        toolbar.draw(pygame.Surface((width, 700)), Keymap(), update_state(), (-1, -1))
        hidden = hidden or toolbar.hits.rect_for("update") is None
    assert hidden


def test_wide_window_still_draws_the_full_update_control():
    toolbar = Toolbar()
    toolbar.draw(pygame.Surface((1600, 700)), Keymap(), update_state(), (-1, -1))
    full = button_rect("Update to 1.2.0", (0, 0), size=15)
    assert toolbar.hits.rect_for("update").w == full.w
    assert toolbar.hits.rect_for("update_dismiss") is not None


def test_toolbar_button_labels_are_screen_saver_and_flash():
    assert dict(i for i in toolbar_module.ITEMS if i)["screensaver"] == "Screen Saver"
    assert dict(i for i in toolbar_module.ITEMS if i)["flash"] == "Flash"
    toolbar = Toolbar()
    toolbar.draw(pygame.Surface((1400, 700)), Keymap(),
                 ToolbarState("medium", False, True, 0, 0.0), (-1, -1))
    assert toolbar.hits.rect_for("screensaver").w == button_rect("Screen Saver", (0, 0), size=15).w
    assert toolbar.hits.rect_for("flash").w == button_rect("Flash", (0, 0), size=15).w


def test_flash_button_tooltip_keeps_flash_finish(monkeypatch):
    seen = drawn_texts(monkeypatch)
    toolbar = Toolbar()
    surface = pygame.Surface((1400, 700))
    state = ToolbarState("medium", False, True, 0, 0.0)
    toolbar.draw(surface, Keymap(), state, (-1, -1))
    seen.clear()
    toolbar.draw(surface, Keymap(), state, toolbar.hits.rect_for("flash").center)
    assert any(s.startswith("Flash finish") for s, _ in seen)
