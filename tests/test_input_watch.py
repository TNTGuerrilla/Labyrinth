from maze_saver.input_watch import ExitWatcher


def test_grace_period_ignores_everything_and_tracks_origin():
    w = ExitWatcher(0.0, (100, 100))
    assert not w.should_exit(0.2, (500, 500), True)
    assert not w.should_exit(0.6, (500, 500), False)


def test_small_moves_are_jitter():
    w = ExitWatcher(0.0, (100, 100))
    assert not w.should_exit(1.0, (105, 105), False)
    assert not w.should_exit(1.0, (108, 100), False)


def test_real_move_exits():
    w = ExitWatcher(0.0, (100, 100))
    assert w.should_exit(1.0, (109, 100), False)


def test_input_event_after_grace_exits():
    w = ExitWatcher(0.0, (100, 100))
    assert w.should_exit(0.5, (100, 100), True)
