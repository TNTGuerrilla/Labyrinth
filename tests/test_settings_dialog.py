from labyrinth_update.releases import Release
from labyrinth_update.updater import AVAILABLE, DOWNLOADING, FAILED, READY, Snapshot
from maze_saver.config import Settings
from maze_saver.settings_dialog import FPS_LABELS, parse_fields, update_row

from labyrinth_update.notes import BLANK, HEADING, ITEM, TEXT, NoteLine  # noqa: E402
from labyrinth_update.updater import (CHECK_FAILED, CHECKING, UP_TO_DATE,  # noqa: E402
                                      CheckReport)
from maze_saver.settings_dialog import note_segments  # noqa: E402

REL = Release("1.2.0", "https://example.test/Labyrinth.scr", "ab" * 32)

VALID = {"min_cells": "10", "max_cells": "30", "gen_speed": "80", "solve_speed": "25",
         "lookahead": "4", "hold_seconds": "2.5", "max_leads": "8", "coverage": "90"}


def test_valid_fields():
    settings, error = parse_fields(VALID, FPS_LABELS[120])
    assert error is None
    assert settings == Settings(min_cells=10, max_cells=30, gen_speed=80.0, solve_speed=25.0,
                                lookahead=4, hold_seconds=2.5, max_leads=8, fps_cap=120,
                                coverage=90)


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


def test_coverage_field_follows_maximum_leads_and_steps_by_5():
    from maze_saver.settings_dialog import FIELDS, INCREMENTS
    names = [name for name, _ in FIELDS]
    assert names[names.index("max_leads") + 1] == "coverage"
    assert dict(FIELDS)["coverage"] == "Screen coverage (%)"
    assert INCREMENTS["coverage"] == 5


def test_coverage_out_of_range():
    for text in ("45", "105"):
        settings, error = parse_fields({**VALID, "coverage": text}, FPS_LABELS["auto"])
        assert settings is None and "Screen coverage (%) must be between 50 and 100" in error


def test_lookahead_out_of_range():
    settings, error = parse_fields({**VALID, "lookahead": "13"}, FPS_LABELS["auto"])
    assert settings is None and "between 0 and 12" in error


def test_check_updates_is_saved():
    settings, _ = parse_fields(VALID, FPS_LABELS["auto"], check_updates=False)
    assert settings.check_updates is False
    assert parse_fields(VALID, FPS_LABELS["auto"])[0].check_updates is True


def test_update_row():
    assert update_row(Snapshot(), "1.0.1") == ("Version 1.0.1", False, False)
    assert update_row(Snapshot(AVAILABLE, REL), "1.0.1") == ("Version 1.2.0 is available.",
                                                             True, True)
    assert update_row(Snapshot(DOWNLOADING, REL, 0.42), "1.0.1") == (
        "Downloading version 1.2.0: 42%", False, False)
    message, can_update, can_dismiss = update_row(Snapshot(READY, REL), "1.0.1")
    assert message.startswith("Updated to version 1.2.0") and not can_update and not can_dismiss
    assert update_row(Snapshot(FAILED, REL, message="Update needs administrator permission."),
                      "1.0.1") == ("Update needs administrator permission.", True, True)


def test_update_row_reports_checks():
    assert update_row(Snapshot(), "1.0.1", CheckReport(CHECKING)) == ("Checking...", False, False)
    assert update_row(Snapshot(), "1.0.1", CheckReport(UP_TO_DATE)) == ("Up to date", False, False)
    assert update_row(Snapshot(), "1.0.1", CheckReport(CHECK_FAILED, "Offline.")) == (
        "Offline.", False, False)
    assert update_row(Snapshot(AVAILABLE, REL), "1.0.1", CheckReport(UP_TO_DATE)) == (
        "Version 1.2.0 is available.", True, True)


def test_update_row_keeps_buttons_while_a_later_check_runs():
    # An offer already on the snapshot keeps its Update and Dismiss buttons while an
    # automatic or forced check is in flight; only the status text says "Checking...".
    assert update_row(Snapshot(AVAILABLE, REL), "1.0.1", CheckReport(CHECKING)) == (
        "Checking...", True, True)
    assert update_row(Snapshot(FAILED, REL, message="Offline."), "1.0.1",
                      CheckReport(CHECKING)) == ("Checking...", True, True)
    assert update_row(Snapshot(), "1.0.1", CheckReport(CHECKING)) == (
        "Checking...", False, False)


def test_note_segments():
    lines = [NoteLine(HEADING, "New"), NoteLine(ITEM, "Faster"), NoteLine(BLANK),
             NoteLine(TEXT, "Thanks")]
    assert note_segments(lines) == [("New\n", "heading"), ("- Faster\n", "item"),
                                     ("\n", "text"), ("Thanks", "text")]
    assert note_segments([]) == []
