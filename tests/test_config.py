import sys
from pathlib import Path

from maze_saver.config import Settings, app_data, default_path, from_dict, load, save


def test_defaults():
    s = Settings()
    assert (s.min_cells, s.max_cells, s.gen_speed, s.solve_speed, s.lookahead, s.hold_seconds,
            s.max_leads, s.fps_cap) == (12, 40, 60.0, 20.0, 4, 4.0, 12, "auto")


def test_missing_file_gives_defaults(tmp_path):
    assert load(tmp_path / "nope.json") == Settings()


def test_invalid_json_gives_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("{not json", encoding="utf-8")
    assert load(p) == Settings()


def test_non_object_json_gives_defaults(tmp_path):
    p = tmp_path / "config.json"
    p.write_text("[1, 2]", encoding="utf-8")
    assert load(p) == Settings()


def test_bad_values_fall_back_per_key():
    s = from_dict({"min_cells": 2, "max_cells": 50, "gen_speed": "fast", "solve_speed": 30,
                   "hold_seconds": 99, "fps_cap": 75, "extra": 1})
    assert s == Settings(max_cells=50, solve_speed=30.0)


def test_bool_is_not_a_number():
    assert from_dict({"min_cells": True, "gen_speed": False}) == Settings()


def test_integral_float_accepted_for_int_field():
    s = from_dict({"min_cells": 20.0})
    assert s.min_cells == 20 and isinstance(s.min_cells, int)


def test_fractional_value_rejected_for_int_field():
    assert from_dict({"min_cells": 20.5}).min_cells == 12


def test_min_greater_than_max_is_swapped():
    s = from_dict({"min_cells": 30, "max_cells": 10})
    assert (s.min_cells, s.max_cells) == (10, 30)


def test_fps_cap_choices():
    for value in ("auto", 60, 120):
        assert from_dict({"fps_cap": value}).fps_cap == value
    assert from_dict({"fps_cap": 60.0}).fps_cap == 60
    assert from_dict({"fps_cap": True}).fps_cap == "auto"


def test_round_trip(tmp_path):
    p = tmp_path / "config.json"
    s = Settings(min_cells=8, max_cells=30, gen_speed=120.0, solve_speed=15.5, lookahead=6,
                 hold_seconds=0.0, max_leads=16, fps_cap=120)
    save(s, p)
    assert load(p) == s


def test_lookahead_bad_values_fall_back_to_default():
    assert from_dict({"lookahead": -1}).lookahead == 4
    assert from_dict({"lookahead": 13}).lookahead == 4


def test_lookahead_accepts_bounds():
    assert from_dict({"lookahead": 0}).lookahead == 0
    assert from_dict({"lookahead": 12}).lookahead == 12


def test_max_leads_bad_values_fall_back_to_default():
    assert from_dict({"max_leads": 1}).max_leads == 12
    assert from_dict({"max_leads": 17}).max_leads == 12


def test_max_leads_accepts_upper_bound():
    assert from_dict({"max_leads": 16}).max_leads == 16


def test_save_creates_parent_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "config.json"
    save(Settings(), p)
    assert p.exists()


def test_default_path_uses_the_settings_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert default_path() == tmp_path / "Labyrinth Screensaver" / "config.json"


def test_settings_carry_over_from_the_pre_rename_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save(Settings(max_leads=5), tmp_path / "MazeScreensaver" / "config.json")
    assert load().max_leads == 5
    assert (tmp_path / "Labyrinth Screensaver" / "config.json").exists()


def test_new_settings_win_over_the_pre_rename_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    save(Settings(max_leads=5), tmp_path / "MazeScreensaver" / "config.json")
    save(Settings(max_leads=7))
    assert load().max_leads == 7


def test_windows_settings_live_in_appdata(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert app_data() == tmp_path


def test_linux_settings_follow_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert app_data() == tmp_path


def test_linux_settings_default_to_dot_config(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert app_data() == tmp_path / ".config"


def test_check_updates_setting(tmp_path):
    from maze_saver.config import Settings, from_dict, load, save
    assert Settings().check_updates is True
    assert from_dict({"check_updates": False}).check_updates is False
    assert from_dict({"check_updates": 0}).check_updates is True
    path = tmp_path / "config.json"
    save(Settings(check_updates=False), path)
    assert load(path).check_updates is False
