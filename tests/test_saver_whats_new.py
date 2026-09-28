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
