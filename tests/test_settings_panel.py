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
    glide_index = next(i for i, row in enumerate(p.model.rows()) if row.name == "glide_speed")
    p.click(p.hits.rect_for(("inc", glide_index)).center)
    assert p.model.draft.glide_speed == 6.0
    bends_index = next(i for i, row in enumerate(p.model.rows()) if row.name == "follow_bends")
    p.click(p.hits.rect_for(("inc", bends_index)).center)
    assert p.model.draft.follow_bends is False


def test_headers_are_drawn_but_not_clickable():
    p = panel()
    surface = pygame.Surface((1280, 720))
    p.draw(surface)
    assert p.model.rows()[0].kind == "header"
    assert p.hits.rect_for(("row", 0)) is None
    first = p.hits.rect_for(("row", 1))
    header_spot = (first.x + 12, first.y - 12)  # the header line sits just above
    assert tuple(surface.get_at(header_spot))[:3] != (0, 0, 0)
    assert p.click(header_spot) is None and p.model.selected.name == "follow_bends"


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


from maze_game.ui.settings_model import InfoState  # noqa: E402


def test_info_links_are_clickable_and_info_lines_are_not():
    p = SettingsPanel(SettingsModel(GameSettings(), Keymap(), 800, (1920, 1040),
                                    info=InfoState("1.2.0", True, "Up to date")))
    p.model.set_tab(3)
    p.draw(pygame.Surface((1280, 720)))
    rows = p.model.rows()
    github = next(i for i, row in enumerate(rows) if row.name == "github")
    version = next(i for i, row in enumerate(rows) if row.name == "version")
    assert p.hits.rect_for(("row", version)) is None
    assert p.click(p.hits.rect_for(("row", github)).center) == "github"


def test_check_now_button_hit_area_is_the_button_not_the_row():
    p = SettingsPanel(SettingsModel(GameSettings(), Keymap(), 800, (1920, 1040),
                                    info=InfoState("1.2.0", True, "Up to date")))
    p.model.set_tab(3)
    surface = pygame.Surface((1280, 720))
    p.draw(surface)
    rows = p.model.rows()
    check_now = next(i for i, row in enumerate(rows) if row.name == "check_now")
    btn = p.hits.rect_for(("row", check_now))
    assert btn is not None
    assert p.click(btn.center) == "check_now"
    far_right = (btn.right + 150, btn.centery)
    assert p.hits.at(far_right) is None
    assert p.click(far_right) is None


def test_selected_info_button_row_draws_no_full_row_highlight():
    p = SettingsPanel(SettingsModel(GameSettings(), Keymap(), 800, (1920, 1040),
                                    info=InfoState("1.2.0", True, "Up to date")))
    p.model.set_tab(3)
    surface = pygame.Surface((1280, 720))
    p.draw(surface)
    rows = p.model.rows()
    check_now = next(i for i, row in enumerate(rows) if row.name == "check_now")
    p.model.select(check_now)
    p.draw(surface)
    btn = p.hits.rect_for(("row", check_now))
    sample = (btn.right + 60, btn.centery)
    from maze_game.ui.widgets import HILITE
    assert tuple(surface.get_at(sample))[:3] != HILITE


def test_fixed_rows_are_drawn_without_a_hit_area():
    p = panel()
    p.model.set_tab(2)
    p.draw(pygame.Surface((1280, 2000)))  # tall enough to draw every Controls row
    rows = p.model.rows()
    fixed = [i for i, r in enumerate(rows) if r.kind == "fixed"]
    assert fixed
    for i in fixed:
        assert p.hits.rect_for(("row", i)) is None
