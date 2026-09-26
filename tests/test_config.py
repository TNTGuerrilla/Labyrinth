from maze_saver.config import Settings, default_path, from_dict, load, save


def test_defaults():
    s = Settings()
    assert (s.min_cells, s.max_cells, s.gen_speed, s.solve_speed, s.hold_seconds, s.max_leads,
            s.fps_cap) == (12, 40, 60.0, 20.0, 4.0, 12, "auto")


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
    s = Settings(min_cells=8, max_cells=30, gen_speed=120.0, solve_speed=15.5,
                 hold_seconds=0.0, max_leads=16, fps_cap=120)
    save(s, p)
    assert load(p) == s


def test_max_leads_bad_values_fall_back_to_default():
    assert from_dict({"max_leads": 1}).max_leads == 12
    assert from_dict({"max_leads": 17}).max_leads == 12


def test_max_leads_accepts_upper_bound():
    assert from_dict({"max_leads": 16}).max_leads == 16


def test_save_creates_parent_dirs(tmp_path):
    p = tmp_path / "a" / "b" / "config.json"
    save(Settings(), p)
    assert p.exists()


def test_default_path_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert default_path() == tmp_path / "MazeScreensaver" / "config.json"
