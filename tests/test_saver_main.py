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
