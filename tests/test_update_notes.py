from labyrinth_update.notes import (BLANK, HEADING, ITEM, MORE_TEXT, TEXT, NoteLine,
                                    extract_notes, fit_lines, parse_notes, wrap_notes)

BODY = ("\r\n\r\n## Changes\r\n- **Faster** mazes\r\n* Fixed `x`\r\n\r\n\r\nThanks!\r\n\r\n"
        "---\r\nSHA-256: abc\r\n## Install\r\n")


def measure(text):
    return 10 * len(text)


def test_extract_cuts_at_the_rule_and_trims():
    assert extract_notes(BODY) == "## Changes\n- **Faster** mazes\n* Fixed `x`\n\n\nThanks!"


def test_extract_keeps_everything_without_a_rule():
    assert extract_notes("a\n--- not a rule\nb\n") == "a\n--- not a rule\nb"


def test_extract_empty():
    for body in (None, "", "\n\n", "---\nonly the tail", 5):
        assert extract_notes(body) == ""


def test_parse_notes():
    assert parse_notes(extract_notes(BODY)) == [
        NoteLine(HEADING, "Changes"), NoteLine(ITEM, "Faster mazes"), NoteLine(ITEM, "Fixed x"),
        NoteLine(BLANK), NoteLine(TEXT, "Thanks!")]


def test_wrap_breaks_at_spaces_and_indents_items():
    lines = [NoteLine(TEXT, "aaa bbb ccc"), NoteLine(ITEM, "ddd eee fff")]
    assert wrap_notes(lines, 70, measure) == [
        NoteLine(TEXT, "aaa bbb"), NoteLine(TEXT, "ccc", cont=True),
        NoteLine(ITEM, "ddd"), NoteLine(ITEM, "eee", cont=True),
        NoteLine(ITEM, "fff", cont=True)]


def test_wrap_cuts_words_longer_than_the_line():
    assert wrap_notes([NoteLine(TEXT, "abcdefgh")], 30, measure) == [
        NoteLine(TEXT, "abc"), NoteLine(TEXT, "def", cont=True), NoteLine(TEXT, "gh", cont=True)]


def test_wrap_keeps_blank_lines():
    assert wrap_notes([NoteLine(BLANK)], 30, measure) == [NoteLine(BLANK)]


def test_fit_lines():
    lines = [NoteLine(TEXT, str(i)) for i in range(5)]
    more = [NoteLine(TEXT, MORE_TEXT)]
    assert fit_lines(lines, 5, more) == lines
    assert fit_lines(lines, 3, more) == lines[:2] + more
    spaced = [NoteLine(TEXT, "a"), NoteLine(BLANK), NoteLine(TEXT, "b"), NoteLine(TEXT, "c")]
    assert fit_lines(spaced, 3, more) == [NoteLine(TEXT, "a")] + more
    assert fit_lines(lines, 0, more) == []


from labyrinth_update.notes import NoteEntry, collect_notes, merge_notes  # noqa: E402
from labyrinth_update.releases import GAME_WINDOWS  # noqa: E402


def rel(tag, body="", draft=False, prerelease=False):
    return {"tag_name": tag, "body": body, "draft": draft, "prerelease": prerelease,
            "assets": []}


def test_collect_notes_of_newer_releases_newest_first():
    listing = [rel("labyrinth-v1.4.0", "Four"), rel("labyrinth-v1.3.0", "Three\n---\nsha"),
               rel("labyrinth-v1.2.1", ""), rel("labyrinth-v1.2.0", "Two"),
               rel("labyrinth-v1.1.0", "One"), rel("labyrinth-v1.3.5", "d", draft=True),
               rel("labyrinth-v1.3.6", "p", prerelease=True),
               rel("labyrinth-screensaver-v1.3.0", "Other product"), None, {"tag_name": 5},
               {"tag_name": "labyrinth-v1.2.5", "body": None}]
    assert collect_notes(listing, GAME_WINDOWS, "1.1.0", "1.3.0") == [
        NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two")]


def test_collect_orders_numerically_and_rejects_bad_input():
    listing = [rel("labyrinth-v1.9.0", "Nine"), rel("labyrinth-v1.10.0", "Ten")]
    assert [e.version for e in collect_notes(listing, GAME_WINDOWS, "1.0.0", "1.10.0")] == [
        "1.10.0", "1.9.0"]
    assert collect_notes("junk", GAME_WINDOWS, "1.0.0", "2.0.0") == []
    assert collect_notes(listing, GAME_WINDOWS, "bad", "2.0.0") == []


def test_merge_keeps_unshown_notes_and_adds_new_ones():
    stored = (NoteEntry("1.2.0", "Two"), NoteEntry("1.1.0", "One"), NoteEntry("1.5.0", "Pulled"))
    fresh = [NoteEntry("1.4.0", "Four"), NoteEntry("1.3.0", "Three")]
    assert merge_notes(stored, fresh, "1.2.0") == (
        NoteEntry("1.4.0", "Four"), NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two"),
        NoteEntry("1.1.0", "One"))


from labyrinth_update.notes import has_notes, notes_for_run  # noqa: E402

RUN_LISTING = [rel("labyrinth-v1.6.0", "Six"), rel("labyrinth-v1.5.0", "Five\n---\nsha"),
               rel("labyrinth-v1.4.1", "d", draft=True), rel("labyrinth-v1.4.0", "Four"),
               rel("labyrinth-v1.3.0", ""), rel("labyrinth-v1.2.0", "Two"),
               rel("labyrinth-screensaver-v1.5.0", "Other product")]


def test_notes_for_run_is_the_running_version_alone_when_nothing_is_pending():
    for last_run in (None, "1.5.0", "1.7.0", "bad"):
        assert notes_for_run(RUN_LISTING, GAME_WINDOWS, "1.5.0", last_run) == [
            NoteEntry("1.5.0", "Five")]


def test_notes_for_run_covers_every_skipped_version_while_pending():
    assert notes_for_run(RUN_LISTING, GAME_WINDOWS, "1.5.0", "1.2.0") == [
        NoteEntry("1.5.0", "Five"), NoteEntry("1.4.0", "Four")]


def test_notes_for_run_handles_bad_input():
    assert notes_for_run("junk", GAME_WINDOWS, "1.5.0", None) == []
    assert notes_for_run(RUN_LISTING, GAME_WINDOWS, "bad", None) == []
    assert notes_for_run(RUN_LISTING, GAME_WINDOWS, "1.3.0", None) == []  # empty notes


def test_has_notes():
    notes = (NoteEntry("1.5.0", "Five"), NoteEntry("1.4.0", "Four"))
    assert has_notes(notes, "1.5.0") and has_notes(notes, "1.4.0")
    assert not has_notes(notes, "1.3.0") and not has_notes((), "1.5.0")
    assert not has_notes(notes, "bad")
