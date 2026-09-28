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
