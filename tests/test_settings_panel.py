import pygame
import pytest

from maze_game.config import GameSettings
from maze_game.keymap import Keymap
from maze_game.ui.settings_model import SettingsModel
from maze_game.ui.settings_panel import SettingsPanel


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def panel():
    return SettingsPanel(SettingsModel(GameSettings(), Keymap(), 800, (1920, 1040)))


def test_clicking_a_tab_switches_tabs():
    p = panel()
    p.draw(pygame.Surface((1280, 720)))
    p.click(p.hits.rect_for(("tab", 2)).center)
    assert p.model.tab == 2


def test_clicking_arrows_changes_values():
    p = panel()
    p.draw(pygame.Surface((1280, 720)))
    p.click(p.hits.rect_for(("inc", 3)).center)
    assert p.model.draft.glide_speed == 15.0
    p.click(p.hits.rect_for(("inc", 0)).center)
    assert p.model.draft.follow_bends is False


def test_clicking_apply_returns_apply():
    p = panel()
    p.draw(pygame.Surface((1280, 720)))
    apply_index = len(p.model.rows()) - 2
    assert p.click(p.hits.rect_for(("row", apply_index)).center) == "apply"


def test_long_tab_scrolls_to_the_selection():
    p = panel()
    p.model.set_tab(2)
    last = len(p.model.rows()) - 3
    p.model.select(last)
    p.draw(pygame.Surface((800, 500)))
    assert p.hits.rect_for(("row", last)) is not None


def test_keyboard_calls_pass_through():
    p = panel()
    assert p.handle("cancel") == "cancel"
    p.model.set_tab(2)
    p.handle("confirm")
    assert p.capturing
    p.capture("h")
    assert not p.capturing and p.model.keys.keys_for("up")[0] == "h"
