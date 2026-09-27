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
    {"up": ["w"]},
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


def test_key_label():
    assert key_label("q") == "Q"
    assert key_label("space") == "Space"
    assert key_label("f11") == "F11"
    assert key_label("[+]") == "Num +"
