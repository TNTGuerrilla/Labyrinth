from maze_game.config import GameSettings
from maze_game.keymap import Keymap
from maze_game.ui.settings_model import GAMEPLAY_ROWS, SettingsModel


def model(**kw):
    return SettingsModel(GameSettings(**kw), Keymap(), ceiling=800, resolution=(1920, 1040))


def row_index(m, name):
    return next(i for i, row in enumerate(m.rows()) if row.name == name)


def test_every_tab_ends_with_apply_and_cancel():
    m = model()
    for tab in range(3):
        m.set_tab(tab)
        assert [row.name for row in m.rows()[-2:]] == ["apply", "cancel"]


def test_tab_key_cycles_tabs():
    m = model()
    m.handle("tab")
    assert m.tab == 1 and m.index == 0
    assert [row.name for row in m.rows()[:4]] == ["difficulty", "custom_min", "custom_max",
                                                  "benchmark"]


def test_navigation_wraps():
    m = model()
    m.handle("up")
    assert m.index == len(m.rows()) - 1


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
    assert m.draft.glide_speed == 15.0
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
    assert m.value_text(GAMEPLAY_ROWS[0]) == "On"
    assert m.value_text(GAMEPLAY_ROWS[1]) == "Animated"
    assert m.value_text(GAMEPLAY_ROWS[3]) == "14"
    m.set_tab(2)
    assert m.value_text(m.rows()[row_index(m, "hint")]) == "Q"


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
