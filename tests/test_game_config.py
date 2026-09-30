import json
from dataclasses import replace
import os
from pathlib import Path

import pytest

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
    p.write_text(json.dumps({"settings": {"hint_length": 12}, "keys": {"up": "w"}}),
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


def test_an_oversized_integer_falls_back_for_that_field(tmp_path):
    p = tmp_path / "config.json"
    huge = "9" * 400
    p.write_text('{"settings": {"grid_strength": %s, "glide_speed": %s, "hint_length": 12}}'
                 % (huge, huge), encoding="utf-8")
    s, k = load(p)
    assert s == GameSettings(hint_length=12) and k == Keymap()


def test_an_oversized_integer_in_the_benchmark_does_not_raise(tmp_path):
    p = tmp_path / "config.json"
    huge = "9" * 400
    p.write_text('{"settings": {"bench_size": %s, "bench_rate": 1e-6, '
                 '"bench_resolution": [800, 600], "coverage": 75}}' % huge, encoding="utf-8")
    assert load(p)[0] == GameSettings(coverage=75)
    p.write_text('{"settings": {"bench_size": 100, "bench_rate": 1e-6, '
                 '"bench_resolution": [%s, 600]}}' % huge, encoding="utf-8")
    assert load(p)[0].bench_resolution == (int(huge), 600)  # never matches a screen


def test_deeply_nested_json_gives_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("[" * 100_000 + "]" * 100_000, encoding="utf-8")
    assert load(p) == (GameSettings(), Keymap())


def test_save_replaces_the_file_through_a_temp_file(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    p.write_text("old", encoding="utf-8")
    replaced = []
    real = os.replace
    monkeypatch.setattr(os, "replace", lambda a, b: (replaced.append((Path(a), Path(b))),
                                                     real(a, b)))
    save(GameSettings(hint_length=12), Keymap(), p)
    assert load(p)[0].hint_length == 12
    assert len(replaced) == 1 and replaced[0][1] == p and replaced[0][0].parent == tmp_path
    assert sorted(f.name for f in tmp_path.iterdir()) == ["config.json"]


def test_a_failed_replace_leaves_the_old_file_and_no_temp_file(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    p.write_text("old", encoding="utf-8")

    def boom(a, b):
        raise OSError("locked")
    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        save(GameSettings(), Keymap(), p)
    assert p.read_text(encoding="utf-8") == "old"
    assert sorted(f.name for f in tmp_path.iterdir()) == ["config.json"]


def test_benchmark_coverage_round_trips_and_validates(tmp_path):
    p = tmp_path / "config.json"
    s = GameSettings(coverage=75, bench_size=300, bench_rate=2e-6,
                     bench_resolution=(1920, 1040), bench_coverage=75)
    save(s, Keymap(), p)
    assert load(p)[0] == s
    bench = {"bench_size": 100, "bench_rate": 1e-6, "bench_resolution": [800, 600]}
    assert from_dict(bench).bench_coverage == 100  # saved before coverage was stored
    assert from_dict(dict(bench, bench_coverage=60)).bench_coverage == 60
    for bad in (49, 101, 80.5, "80", True, None):
        assert from_dict(dict(bench, bench_coverage=bad)).bench_size is None


def test_screensaver_settings_defaults():
    s = GameSettings()
    assert (s.screensaver_solver, s.screensaver_speed, s.screensaver_lookahead,
            s.screensaver_pause) == ("human", 20.0, 4, 4.0)


def test_screensaver_settings_load_and_fall_back():
    s = from_dict({"screensaver_solver": "wall", "screensaver_speed": 80,
                   "screensaver_lookahead": 0, "screensaver_pause": 0.5})
    assert (s.screensaver_solver, s.screensaver_speed, s.screensaver_lookahead,
            s.screensaver_pause) == ("wall", 80.0, 0, 0.5)
    bad = from_dict({"screensaver_solver": "zig", "screensaver_speed": 1,
                     "screensaver_lookahead": 13, "screensaver_pause": 31})
    assert bad == GameSettings()


def test_screensaver_settings_round_trip(tmp_path):
    path = tmp_path / "config.json"
    s = replace(GameSettings(), screensaver_solver="dfs", screensaver_pause=2.5)
    save(s, Keymap(), path)
    assert load(path)[0] == s
