from labyrinth_update.notes import BLANK, HEADING, RELEASES_TEXT, TEXT, NoteEntry, NoteLine
from labyrinth_update.state import UpdateState
from labyrinth_update.whats_new import (SHOW_RUNS, WhatsNew, count_run, mark_seen, on_start,
                                        pending, running_notes)

NOTES = (NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two"), NoteEntry("1.1.0", "One"))


def test_fresh_install_records_the_version_and_shows_nothing():
    state, shown = on_start(UpdateState(notes=NOTES), "1.2.0")
    assert shown is None and state.last_run_version == "1.2.0"


def test_same_version_shows_nothing():
    state = UpdateState(last_run_version="1.2.0", notes=NOTES)
    assert on_start(state, "1.2.0") == (state, None)


def test_a_downgrade_shows_nothing():
    state = UpdateState(last_run_version="1.3.0")
    assert on_start(state, "1.2.0") == (state, None)


def test_older_stored_version_shows_the_new_notes():
    state = UpdateState(last_run_version="1.1.0", notes=NOTES)
    after, shown = on_start(state, "1.2.0")
    assert after == state  # it counts as seen only later
    assert shown == WhatsNew("1.2.0", (NoteEntry("1.2.0", "Two"),))
    assert shown.lines() == [NoteLine(TEXT, "Two")]


def test_a_skipped_version_shows_both_with_headings():
    shown = on_start(UpdateState(last_run_version="1.1.0", notes=NOTES), "1.3.0")[1]
    assert shown.lines() == [
        NoteLine(HEADING, "Version 1.3.0"), NoteLine(TEXT, "Three"), NoteLine(BLANK),
        NoteLine(HEADING, "Version 1.2.0"), NoteLine(TEXT, "Two")]


def test_no_notes_gives_the_fallback():
    shown = on_start(UpdateState(last_run_version="1.1.0"), "1.2.0")[1]
    assert shown.lines() == [NoteLine(TEXT, "Updated to version 1.2.0."),
                             NoteLine(TEXT, RELEASES_TEXT)]


def test_seen_keeps_only_what_this_update_brought():
    state = mark_seen(UpdateState(last_run_version="1.1.0", notes=NOTES, whats_new_runs=2),
                      "1.2.0")
    assert state.last_run_version == "1.2.0" and state.whats_new_runs == 0
    assert state.notes == NOTES[:2]
    assert not pending(state, "1.2.0")
    assert mark_seen(state, "1.2.0") == state  # seeing it again changes nothing
    assert running_notes(state, "1.2.0") == WhatsNew("1.2.0", (NoteEntry("1.2.0", "Two"),))


def test_running_notes_before_it_was_seen():
    state = UpdateState(last_run_version="1.1.0", notes=NOTES)
    assert running_notes(state, "1.2.0").entries == (NoteEntry("1.2.0", "Two"),)
    assert running_notes(UpdateState(last_run_version="1.2.0"), "1.2.0").entries == ()


def test_the_screensaver_shows_it_in_at_most_three_runs():
    state = UpdateState(last_run_version="1.1.0", notes=NOTES)
    for run in range(1, SHOW_RUNS):
        state = count_run(state, "1.2.0")
        assert state.whats_new_runs == run and pending(state, "1.2.0")
    state = count_run(state, "1.2.0")
    assert not pending(state, "1.2.0") and state.last_run_version == "1.2.0"
