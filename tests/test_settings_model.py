from maze_game.config import GameSettings
from maze_game.keymap import ACTIONS, SLOTS, Keymap
from maze_game.ui.settings_model import SettingsModel


def model(**kw):
    return SettingsModel(GameSettings(**kw), Keymap(), ceiling=800, resolution=(1920, 1040))


def row_index(m, name):
    return next(i for i, row in enumerate(m.rows()) if row.name == name)


def test_every_tab_ends_with_apply_and_cancel():
    m = model()
    for tab in range(4):
        m.set_tab(tab)
        assert [row.name for row in m.rows()[-2:]] == ["apply", "cancel"]


def names(m):
    return [row.name for row in m.rows() if row.kind != "header"]


def headers(m):
    return [row.label for row in m.rows() if row.kind == "header"]


def test_tab_key_cycles_tabs():
    m = model()
    m.handle("tab")
    assert m.tab == 1 and m.selected.name == "difficulty"
    assert names(m)[:4] == ["difficulty", "custom_min", "custom_max", "benchmark"]


def test_every_tab_is_split_into_sections():
    m = model()
    assert headers(m) == ["Movement", "Display", "Maze growth", "Assists"]
    assert names(m)[:3] == ["follow_bends", "glide_speed", "turn_pause"]
    m.set_tab(1)
    assert headers(m) == ["Maze size", "Performance"]
    m.set_tab(2)
    assert headers(m) == ["Movement", "Assists", "Round", "Maze size", "View", "Menu"]
    assert m.rows()[0].kind == "header"
    key_rows = [(row.name, row.slot) for row in m.rows() if row.kind == "key"]
    assert sorted(key_rows) == sorted((a, s) for a in ACTIONS for s in range(SLOTS[a]))


def test_headers_are_never_selected():
    m = model()
    assert m.selected.name == "follow_bends"  # the header above it is skipped
    for _ in range(len(m.rows()) * 2):
        m.handle("down")
        assert m.selected.kind != "header"
    for _ in range(len(m.rows()) * 2):
        m.handle("up")
        assert m.selected.kind != "header"
    m.select(0)
    assert m.selected.kind != "header"
    m.set_tab(3)
    for _ in range(len(m.rows()) * 2):
        m.handle("down")
        assert m.selected.kind != "header" and m.selected.kind != "info"
    for _ in range(len(m.rows()) * 2):
        m.handle("up")
        assert m.selected.kind != "header" and m.selected.kind != "info"


def test_navigation_wraps():
    m = model()
    m.handle("up")
    assert m.index == len(m.rows()) - 1
    m.handle("down")
    assert m.selected.name == "follow_bends"


def test_bool_toggles_with_arrows_and_enter():
    m = model()
    m.handle("right")
    assert m.draft.follow_bends is False
    m.handle("confirm")
    assert m.draft.follow_bends is True


def test_numbers_step_and_clamp():
    m = model()
    m.select(row_index(m, "glide_speed"))
    m.handle("right")
    assert m.draft.glide_speed == 6.0
    for _ in range(100):
        m.handle("right")
    assert m.draft.glide_speed == 40.0


def test_int_fields_stay_int():
    m = model()
    m.select(row_index(m, "lookahead"))
    m.handle("right")
    assert m.draft.lookahead == 5 and isinstance(m.draft.lookahead, int)


def test_choice_cycles():
    m = model()
    m.set_tab(1)
    m.handle("right")
    assert m.draft.difficulty == "large"
    m.handle("left")
    m.handle("left")
    assert m.draft.difficulty == "small"


def test_buttons_and_cancel_return_outcomes():
    m = model()
    m.select(row_index(m, "apply"))
    assert m.handle("confirm") == "apply"
    assert m.handle("cancel") == "cancel"
    m.set_tab(1)
    m.select(row_index(m, "benchmark"))
    assert m.handle("confirm") == "benchmark"


def test_bench_text():
    assert model().bench_text() == "Not run for this screen size"
    done = model(bench_size=300, bench_rate=1e-6, bench_resolution=(1920, 1040))
    assert done.bench_text() == "Recommended max: 300"
    other = model(bench_size=300, bench_rate=1e-6, bench_resolution=(800, 600))
    assert other.bench_text() == "Not run for this screen size"


def test_value_text():
    m = model()
    assert m.value_text(m.rows()[row_index(m, "follow_bends")]) == "On"
    assert m.value_text(m.rows()[row_index(m, "animated")]) == "Animated"
    assert m.value_text(m.rows()[row_index(m, "glide_speed")]) == "5"
    m.set_tab(2)
    assert m.value_text(m.rows()[row_index(m, "hint")]) == "Q"


def test_turn_pause_steps_cleanly():
    m = model()
    m.select(row_index(m, "turn_pause"))
    m.handle("right")
    m.handle("right")
    assert m.draft.turn_pause == 0.3
    assert m.value_text(m.selected) == "0.3"


def test_rebinding_a_free_key():
    m = model()
    m.set_tab(2)
    m.select(row_index(m, "hint"))
    m.handle("confirm")
    assert m.capturing
    m.capture("h")
    assert m.keys.keys_for("hint") == ("h",) and not m.capturing


def test_rebinding_a_used_key_asks_then_swaps():
    m = model()
    m.set_tab(2)
    m.select(row_index(m, "hint"))
    m.handle("confirm")
    m.capture("e")
    assert m.pending_swap == "e" and "Auto-solve" in m.message
    assert m.handle("confirm") is None
    assert m.keys.keys_for("hint") == ("e",) and m.keys.keys_for("autosolve") == ("q",)


def test_cancelling_a_swap_changes_nothing_and_keeps_the_panel_open():
    m = model()
    m.set_tab(2)
    m.select(row_index(m, "hint"))
    m.handle("confirm")
    m.capture("e")
    assert m.handle("cancel") is None
    assert m.keys == Keymap() and m.pending_swap is None


def test_escape_cancels_capture():
    m = model()
    m.set_tab(2)
    m.select(row_index(m, "hint"))
    m.handle("confirm")
    m.capture("escape")
    assert not m.capturing and m.keys == Keymap()


def test_reset_to_defaults():
    m = model()
    m.set_tab(2)
    m.select(row_index(m, "hint"))
    m.handle("confirm")
    m.capture("h")
    m.select(row_index(m, "reset_keys"))
    m.handle("confirm")
    assert m.keys == Keymap()


def test_result_orders_the_custom_range_and_leaves_the_original_alone():
    original = Keymap()
    m = SettingsModel(GameSettings(custom_min=90, custom_max=30), original, 800, (1920, 1040))
    m.keys.set_key("hint", 0, "h")
    settings, keys = m.result()
    assert (settings.custom_min, settings.custom_max) == (30, 90)
    assert keys.keys_for("hint") == ("h",) and original.keys_for("hint") == ("q",)


def test_check_updates_toggles():
    m = model()
    m.set_tab(3)
    m.select(row_index(m, "check_updates"))
    assert m.value_text(m.selected) == "On"
    m.activate()
    assert m.draft.check_updates is False


from maze_game.ui.settings_model import InfoState  # noqa: E402


def test_info_tab_in_a_build():
    m = model()
    m.set_info(InfoState("1.2.0", True, "Up to date", False))
    m.set_tab(3)
    assert [r.label for r in m.rows() if r.kind == "info"] == [
        "Labyrinth 1.2.0", "\u00a9 2026 ByDesign Interactive"]
    assert names(m) == ["version", "copyright", "github", "license", "check_updates",
                        "check_now", "whats_new", "apply", "cancel"]
    assert m.selected.name == "github"  # the info lines are skipped
    rows = {r.name: r for r in m.rows()}
    assert m.value_text(rows["github"]) == "github.com/TNTGuerrilla/Labyrinth"
    assert m.value_text(rows["license"]) == "Licensed under Apache 2.0"
    assert m.value_text(rows["check_now"]) == "Up to date"
    assert m.activate() == "github"
    m.select(row_index(m, "license"))
    assert m.activate() == "license"


def test_info_tab_from_source():
    m = model()
    m.set_tab(3)
    labels = [r.label for r in m.rows() if r.kind == "info"]
    assert "Updates are only available in released builds." in labels
    assert "check_updates" in names(m)
    assert not {"check_now", "update", "whats_new"} & set(names(m))


def test_update_row_appears_without_moving_the_selection():
    m = model()
    m.set_info(InfoState("1.0.0", True))
    m.set_tab(3)
    m.select(row_index(m, "whats_new"))
    m.set_info(InfoState("1.0.0", True, "Version 1.1.0 is available", True))
    assert m.selected.name == "whats_new"
    assert names(m).index("update") == names(m).index("check_now") + 1
