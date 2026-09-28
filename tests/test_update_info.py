from labyrinth_update.info import COPYRIGHT, status_text
from labyrinth_update.releases import Release
from labyrinth_update.updater import (AVAILABLE, CHECK_FAILED, CHECKING, DOWNLOADING, FAILED,
                                      READY, UP_TO_DATE, CheckReport, Snapshot)

REL = Release("1.2.0", "https://example.test/Labyrinth.exe", "ab" * 32)


def test_status_text():
    assert status_text(Snapshot(), CheckReport()) == ""
    assert status_text(Snapshot(), CheckReport(CHECKING)) == "Checking..."
    assert status_text(Snapshot(), CheckReport(UP_TO_DATE)) == "Up to date"
    assert status_text(Snapshot(), CheckReport(CHECK_FAILED, "Offline.")) == "Offline."
    assert status_text(Snapshot(AVAILABLE, REL), CheckReport()) == "Version 1.2.0 is available"
    assert status_text(Snapshot(AVAILABLE, REL), CheckReport(CHECKING)) == "Checking..."
    assert status_text(Snapshot(DOWNLOADING, REL, 0.5), CheckReport(CHECKING)) == "Downloading 50%"
    assert status_text(Snapshot(READY, REL), CheckReport()) == "Restarting"
    assert status_text(Snapshot(FAILED, REL, message="Nope."), CheckReport()) == "Nope."


def test_copyright_uses_the_sign():
    assert COPYRIGHT == "© 2026 ByDesign Interactive"
