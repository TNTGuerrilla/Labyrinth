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


def test_default_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_path() == tmp_path / "MazeGame" / "config.json"


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
