from maze_saver.config import Settings
from maze_saver.settings_dialog import FPS_LABELS, parse_fields

VALID = {"min_cells": "10", "max_cells": "30", "gen_speed": "80", "solve_speed": "25",
         "hold_seconds": "2.5", "max_leads": "8"}


def test_valid_fields():
    settings, error = parse_fields(VALID, FPS_LABELS[120])
    assert error is None
    assert settings == Settings(min_cells=10, max_cells=30, gen_speed=80.0, solve_speed=25.0,
                                hold_seconds=2.5, max_leads=8, fps_cap=120)


def test_not_a_number():
    settings, error = parse_fields({**VALID, "gen_speed": "fast"}, FPS_LABELS["auto"])
    assert settings is None and "Growth speed" in error


def test_whole_number_required():
    settings, error = parse_fields({**VALID, "min_cells": "12.5"}, FPS_LABELS["auto"])
    assert settings is None and "whole number" in error


def test_out_of_range():
    settings, error = parse_fields({**VALID, "hold_seconds": "31"}, FPS_LABELS["auto"])
    assert settings is None and "between 0 and 30" in error


def test_min_above_max_is_swapped():
    settings, _ = parse_fields({**VALID, "min_cells": "50", "max_cells": "20"}, FPS_LABELS[60])
    assert (settings.min_cells, settings.max_cells, settings.fps_cap) == (20, 50, 60)


def test_unknown_fps_label_means_auto():
    settings, _ = parse_fields(VALID, "something else")
    assert settings.fps_cap == "auto"


def test_max_leads_out_of_range():
    settings, error = parse_fields({**VALID, "max_leads": "17"}, FPS_LABELS["auto"])
    assert settings is None and "Maximum leads" in error
