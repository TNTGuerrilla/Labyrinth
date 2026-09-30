import pytest

from maze_game.keymap import ACTIONS, DEFAULTS, LABELS, SLOTS, Keymap, key_label


def test_default_lookups():
    k = Keymap()
    assert k.action_for("w") == "up"
    assert k.action_for("up") == "up"
    assert k.action_for("e") == "autosolve"
    assert k.action_for("[+]") == "zoom_in"
    assert k.action_for("x") is None
    assert k.keys_for("hint") == ("q",)


def test_every_action_has_a_label_and_slot_count():
    assert set(LABELS) == set(ACTIONS)
    assert all(SLOTS[a] == len(DEFAULTS[a]) for a in ACTIONS)


def test_no_default_key_is_used_twice():
    keys = [k for a in ACTIONS for k in DEFAULTS[a]]
    assert len(keys) == len(set(keys))


def test_free_key_replaces_the_slot():
    k = Keymap()
    assert k.set_key("hint", 0, "h")
    assert k.keys_for("hint") == ("h",)
    assert k.action_for("q") is None


def test_used_key_is_swapped():
    k = Keymap()
    assert k.set_key("hint", 0, "e")
    assert k.keys_for("hint") == ("e",)
    assert k.keys_for("autosolve") == ("q",)


def test_swap_within_one_action():
    k = Keymap()
    assert k.set_key("up", 0, "up")
    assert k.keys_for("up") == ("up", "w")


def test_swap_refused_when_it_would_leave_an_action_without_keys():
    raw = Keymap().to_json()
    raw["up"] = ["w"]
    k = Keymap.from_json(raw)
    assert not k.set_key("up", 1, "q")
    assert k.keys_for("hint") == ("q",) and k.keys_for("up") == ("w",)


def test_owner_reports_action_and_slot():
    assert Keymap().owner("down") == ("down", 1)


def test_copy_is_independent():
    a = Keymap()
    b = a.copy()
    b.set_key("hint", 0, "h")
    assert a.keys_for("hint") == ("q",)


def test_json_round_trip():
    k = Keymap()
    k.set_key("hint", 0, "h")
    assert Keymap.from_json(k.to_json()) == k


def _defaults_json():
    return {a: list(keys) for a, keys in DEFAULTS.items()}


@pytest.mark.parametrize("raw", [
    None,
    [],
    {"up": "w"},
    dict(_defaults_json(), hint=[]),
    dict(_defaults_json(), hint=["w"]),
    dict(_defaults_json(), hint=[5]),
    dict(_defaults_json(), hint=["q", "h"]),
])
def test_invalid_json_gives_defaults(raw):
    assert Keymap.from_json(raw) == Keymap()


def test_unknown_key_name_gives_defaults():
    raw = _defaults_json()
    raw["hint"] = ["nope"]
    assert Keymap.from_json(raw, valid_key=lambda n: n != "nope") == Keymap()


def test_empty_key_name_is_refused():
    k = Keymap()
    assert not k.set_key("hint", 0, "")
    assert not k.set_key("up", 1, "")
    assert k == Keymap()


def _custom_json():
    raw = _defaults_json()
    raw["hint"] = ["h"]
    raw["up"] = ["i", "up"]
    return raw


def test_a_missing_action_gets_its_default_and_the_rest_are_kept():
    raw = _custom_json()
    del raw["fullscreen"]
    k = Keymap.from_json(raw)
    assert k.keys_for("hint") == ("h",) and k.keys_for("up") == ("i", "up")
    assert k.keys_for("fullscreen") == ("f11",)


def test_a_bad_action_gets_its_default_and_the_rest_are_kept():
    raw = _custom_json()
    raw["flash"] = ["nope"]
    k = Keymap.from_json(raw, valid_key=lambda n: n != "nope")
    assert k.keys_for("hint") == ("h",) and k.keys_for("flash") == ("f",)


def test_a_default_already_taken_by_a_kept_action_is_left_out():
    raw = _custom_json()
    raw["hint"] = ["d"]  # the default for "right" is ("d", "right")
    del raw["right"]
    k = Keymap.from_json(raw)
    assert k.keys_for("hint") == ("d",) and k.keys_for("right") == ("right",)


def test_actions_sharing_a_key_both_fall_back():
    raw = _custom_json()
    raw["flash"] = ["h"]
    k = Keymap.from_json(raw)
    assert k.keys_for("hint") == ("q",) and k.keys_for("flash") == ("f",)
    assert k.keys_for("up") == ("i", "up")


def test_an_action_left_with_no_key_gives_the_full_defaults():
    raw = _custom_json()
    raw["hint"] = ["f11"]
    del raw["fullscreen"]
    assert Keymap.from_json(raw) == Keymap()


def test_key_label():
    assert key_label("q") == "Q"
    assert key_label("space") == "Space"
    assert key_label("f11") == "F11"
    assert key_label("[+]") == "Num +"


def test_space_is_fixed_and_confirm_is_gone():
    from maze_game.keymap import ACTIONS, FIXED_KEYS
    assert "space" in FIXED_KEYS and "confirm" not in ACTIONS
    assert Keymap().owner("space") is None


def test_space_cannot_be_bound():
    k = Keymap()
    assert k.set_key("hint", 0, "space") is False
    assert k == Keymap()


def test_a_saved_space_binding_resets_only_that_action():
    saved = Keymap().to_json()
    saved["hint"] = ["space"]
    saved["confirm"] = ["x"]  # an old action: ignored
    loaded = Keymap.from_json(saved)
    assert loaded.keys_for("hint") == Keymap().keys_for("hint")
    assert loaded.owner("space") is None and loaded.owner("x") is None


def test_screensaver_action_defaults_to_m():
    from maze_game.keymap import LABELS
    assert Keymap().keys_for("screensaver") == ("m",)
    assert LABELS["screensaver"] == "Start screensaver"


def test_a_saved_keymap_from_before_the_screensaver_action_keeps_its_keys():
    saved = Keymap().to_json()
    del saved["screensaver"]
    saved["hint"] = ["h"]
    loaded = Keymap.from_json(saved)
    assert loaded.keys_for("hint") == ("h",) and loaded.keys_for("screensaver") == ("m",)
