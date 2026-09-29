import json

from maze_game.config import GameSettings, default_path, from_dict, load, save
from maze_game.keymap import Keymap


def test_defaults():
    s = GameSettings()
    assert (s.follow_bends, s.animated, s.multicolor, s.show_grid, s.glide_speed, s.turn_pause,
            s.solve_speed, s.lookahead, s.gen_speed, s.max_leads, s.hint_length, s.difficulty,
            s.custom_min, s.custom_max, s.bench_size, s.bench_rate, s.bench_resolution) == (
        True, True, True, True, 5.0, 0.2, 20.0, 4, 60.0, 12, 8, "medium", 20, 40, None, None,
        None)


def test_new_fields_validate():
    s = from_dict({"turn_pause": 2, "show_grid": 1, "glide_speed": 3})
    assert s == GameSettings(glide_speed=3.0)


def test_default_path_uses_the_settings_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_path() == tmp_path / "Labyrinth" / "config.json"


def test_missing_file_gives_defaults(tmp_path):
    assert load(tmp_path / "nope.json") == (GameSettings(), Keymap())


def test_corrupt_file_gives_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{nope", encoding="utf-8")
    assert load(p) == (GameSettings(), Keymap())


def test_round_trip(tmp_path):
    p = tmp_path / "config.json"
    s = GameSettings(follow_bends=False, difficulty="custom", custom_min=50, custom_max=70,
                     bench_size=300, bench_rate=2e-6, bench_resolution=(1920, 1040))
    k = Keymap()
    k.set_key("hint", 0, "h")
    save(s, k, p)
    assert load(p) == (s, k)


def test_bad_fields_fall_back_one_by_one():
    s = from_dict({"glide_speed": 999, "lookahead": 2.5, "follow_bends": 1,
                   "difficulty": "insane", "hint_length": 12, "multicolor": False})
    assert s == GameSettings(hint_length=12, multicolor=False)


def test_benchmark_fields_need_each_other():
    assert from_dict({"bench_size": 100}) == GameSettings()
    s = from_dict({"bench_size": 100, "bench_rate": 1e-6, "bench_resolution": [800, 600]})
    assert (s.bench_size, s.bench_rate, s.bench_resolution) == (100, 1e-6, (800, 600))


def test_bad_keymap_resets_only_the_keys(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"settings": {"hint_length": 12}, "keys": {"up": ["w"]}}),
                 encoding="utf-8")
    s, k = load(p)
    assert s.hint_length == 12 and k == Keymap()


def test_valid_key_callback_is_used(tmp_path):
    p = tmp_path / "config.json"
    k = Keymap()
    k.set_key("hint", 0, "h")
    save(GameSettings(), k, p)
    assert load(p)[1] == k
    assert load(p, valid_key=lambda name: name != "h")[1] == Keymap()


def test_settings_carry_over_from_the_pre_rename_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save(GameSettings(glide_speed=3.0), Keymap(), tmp_path / "MazeGame" / "config.json")
    assert load()[0].glide_speed == 3.0
    assert (tmp_path / "Labyrinth" / "config.json").exists()


def test_check_updates_round_trip(tmp_path):
    path = tmp_path / "config.json"
    assert GameSettings().check_updates is True
    save(GameSettings(check_updates=False), Keymap(), path)
    assert load(path)[0].check_updates is False


def test_check_updates_must_be_a_bool():
    assert from_dict({"check_updates": "no"}).check_updates is True


def test_grid_strength_defaults_to_20_and_validates():
    assert GameSettings().grid_strength == 20
    assert from_dict({"grid_strength": 10}).grid_strength == 10
    assert from_dict({"grid_strength": 100}).grid_strength == 100
    for bad in (9, 101, 55.5, "50", True):
        assert from_dict({"grid_strength": bad}).grid_strength == 20


def test_coverage_defaults_to_100_and_validates():
    assert GameSettings().coverage == 100
    assert from_dict({"coverage": 75}).coverage == 75
    for bad in (49, 101, 80.5, "80", True):
        assert from_dict({"coverage": bad}).coverage == 100
