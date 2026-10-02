"""maze_saver.__main__ pieces that do not need Windows or a real display. Cross-platform,
unlike tests/test_app.py, so this runs on Linux CI too."""
from labyrinth_update.whats_new import WhatsNew
from maze_saver.__main__ import _whats_new


def test_whats_new_counts_the_run_before_the_screensaver_starts():
    class FakeUpdater:
        def __init__(self, shown):
            self.shown, self.calls = shown, []

        def start_whats_new(self):
            self.calls.append("start")
            return self.shown

        def count_whats_new_run(self):
            self.calls.append("count")

        def mark_whats_new_seen(self):
            self.calls.append("seen")

    assert _whats_new(None) is None
    quiet = FakeUpdater(None)
    assert _whats_new(quiet) is None and quiet.calls == ["start"]
    updater = FakeUpdater(WhatsNew("9.9.9"))
    saver = _whats_new(updater)
    assert updater.calls == ["start", "count"]
    assert saver.title == "Labyrinth Screensaver updated to 9.9.9"
    assert saver.lines == tuple(WhatsNew("9.9.9").lines())
    saver.on_seen()
    assert updater.calls[-1] == "seen"


def test_whats_new_takes_notes_that_arrive_while_it_shows():
    from labyrinth_update.notes import NoteEntry
    from maze_saver.whats_new import with_arrived_notes

    class FakeUpdater:
        def __init__(self):
            self.running = WhatsNew("9.9.9")

        def start_whats_new(self):
            return WhatsNew("9.9.9")

        def count_whats_new_run(self):
            pass

        def mark_whats_new_seen(self):
            pass

        def running_whats_new(self):
            return self.running

    updater = FakeUpdater()
    saver = _whats_new(updater)
    assert with_arrived_notes(saver) is None  # still the fallback text
    arrived = WhatsNew("9.9.9", (NoteEntry("9.9.9", "- Faster"),))
    updater.running = arrived
    fresh = with_arrived_notes(saver)
    assert fresh.lines == tuple(arrived.lines()) and fresh.title == saver.title
    assert with_arrived_notes(fresh) is None  # taken once


def test_whats_new_with_notes_never_changes():
    from labyrinth_update.notes import NoteEntry
    from maze_saver.whats_new import with_arrived_notes

    class FakeUpdater:
        def start_whats_new(self):
            return WhatsNew("9.9.9", (NoteEntry("9.9.9", "Shown"),))

        def count_whats_new_run(self):
            pass

        def mark_whats_new_seen(self):
            pass

        def running_whats_new(self):
            raise AssertionError("not asked again")

    assert with_arrived_notes(_whats_new(FakeUpdater())) is None
