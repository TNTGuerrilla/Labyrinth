from maze_saver.whats_new import (SectionClock, countdown, footer_layout, footer_text,
                                  number_slot)


def measure(text):
    """A proportional font: ones are narrow."""
    return sum(5 if ch == "1" else 9 for ch in text)


def test_countdown_runs_60_to_1_then_stops():
    assert countdown(0.0) == 60 and countdown(0.99) == 60 and countdown(1.0) == 59
    assert countdown(59.5) == 1 and countdown(60.0) is None and countdown(500.0) is None
    assert [countdown(float(t)) for t in range(60)] == list(range(60, 0, -1))


def test_footer_text():
    assert footer_text(60) == ("Closes in ", "60")
    assert footer_text(None) == ("Closes after this maze", "")


def test_the_number_sits_in_a_fixed_slot():
    wide, narrow = footer_layout(60, measure), footer_layout(9, measure)
    assert (wide.number_right, wide.width) == (narrow.number_right, narrow.width)
    assert wide.number_right - measure("60") >= measure("Closes in ")
    assert number_slot(measure) == 18
    after = footer_layout(None, measure)
    assert after.number == "" and after.width == measure("Closes after this maze")


def test_a_solve_before_the_minute_keeps_it_open():
    clock = SectionClock(100.0)
    clock.board_solved(159.9)
    assert clock.closed_at is None and clock.alpha(170.0) == 255 and not clock.faded(500.0)


def test_the_first_solve_after_the_minute_closes_it():
    clock = SectionClock(100.0)
    assert clock.seconds_left(100.0) == 60 and clock.seconds_left(160.0) is None
    clock.board_solved(165.0)
    clock.board_solved(170.0)  # a later solve does not restart the fade
    assert clock.closed_at == 165.0
    assert clock.alpha(165.0) == 255 and clock.alpha(165.75) == 128
    assert not clock.faded(166.4) and clock.faded(166.5) and clock.alpha(166.5) == 0

import pytest  # noqa: E402

from maze_saver.layout import Rect  # noqa: E402
from maze_saver.whats_new import card_size, split_monitor  # noqa: E402


def overlaps(a, b):
    return a.x < b.right and b.x < a.right and a.y < b.bottom and b.y < a.bottom


SIZES = [(1920, 1080), (3440, 1440), (2560, 1440), (1200, 1920), (1920, 1200), (800, 600)]


def expected_card(w, h, factor=1.0):
    """The rule written out: 540 x 690 at a 1440 px shorter side, scaled, then clamped to
    25% of the width (times the TV's factor) and 80% of the height, aspect ratio kept."""
    scale = min(w, h) / 1440 * factor
    cw, ch = 540 * scale, 690 * scale
    k = min(1.0, w / 4 * factor / cw, h * 0.8 / ch)
    return int(cw * k + 0.5), int(ch * k + 0.5)


@pytest.mark.parametrize("size", SIZES)
def test_card_size_follows_the_rule_and_its_clamps(size):
    w, h = size
    cw, ch = card_size(w, h)
    ew, eh = expected_card(w, h)
    assert abs(cw - ew) <= 1 and abs(ch - eh) <= 1
    assert cw <= w / 4 and ch <= h * 0.8
    assert abs(cw / ch - 540 / 690) < 0.01


def test_card_size_examples():
    assert card_size(3440, 1440) == (540, 690)
    assert card_size(2560, 1440) == (540, 690)
    assert card_size(1920, 1080) == (405, 518)
    assert card_size(1920, 1080, 1.25) == (506, 647)  # the TV: 1.25 times the monitor's
    for w, h in SIZES:
        tw, th = card_size(w, h, 1.25)
        ew, eh = expected_card(w, h, 1.25)
        assert abs(tw - ew) <= 1 and abs(th - eh) <= 1 and th <= h * 0.8


@pytest.mark.parametrize("size", SIZES)
def test_card_and_board_never_overlap_and_cover_the_monitor(size):
    w, h = size
    split = split_monitor(w, h)
    card = split.section
    screen = Rect(0, 0, w, h)
    assert (card.w, card.h) == card_size(w, h)
    assert screen.contains(split.board) and screen.contains(card)
    assert not overlaps(split.board, card)
    margin = min(w, h) // 40
    if w >= h:  # landscape: a column on the right, card centred in it
        column = card.w + 2 * margin
        assert split.board == Rect(0, 0, w - column, h)
        assert card.x - split.board.right == margin and w - card.right == margin
        assert abs(card.y - (h - card.bottom)) <= 1
    else:  # portrait: a band at the bottom, card centred in it
        band = card.h + 2 * margin
        assert split.board == Rect(0, 0, w, h - band)
        assert card.y - split.board.bottom == margin and h - card.bottom == margin
        assert abs(card.x - (w - card.right)) <= 1
