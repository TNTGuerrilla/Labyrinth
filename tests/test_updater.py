import json
import threading

from labyrinth_update import updater as updater_module
from labyrinth_update.net import UpdateError
from labyrinth_update.releases import GAME_WINDOWS
from labyrinth_update.updater import (AVAILABLE, DOWNLOADING, FAILED, IDLE, READY, DEBUG_ENV,
                                      Updater, for_program)

DAY = 24 * 3600


def listing(*versions):
    return [{"tag_name": f"labyrinth-v{v}",
             "assets": [{"name": "Labyrinth.exe",
                         "browser_download_url": f"https://example.test/{v}/Labyrinth.exe",
                         "digest": "sha256:" + "ab" * 32}]} for v in versions]


class Fetch:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class BlockingFetch:
    """A fetch that hangs until the test releases it, so a check can be held in flight
    deterministically. `started` fires once the check thread has called in; the test then
    does whatever it needs to overlap with the check before setting `release_event`."""

    def __init__(self, result):
        self.result = result
        self.calls = 0
        self.started = threading.Event()
        self.release_event = threading.Event()

    def __call__(self):
        self.calls += 1
        self.started.set()
        if not self.release_event.wait(5):
            raise AssertionError("BlockingFetch was never released")
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def make(tmp_path, fetch, enabled=True, now=1000.0, current="1.1.0"):
    return Updater(GAME_WINDOWS, current, tmp_path / "update.json", enabled, fetch=fetch,
                   clock=lambda: now)


def checked(u, force=False):
    u.check(force)
    u.wait(5)
    return u.snapshot


def test_first_run_checks_and_offers(tmp_path):
    snap = checked(make(tmp_path, Fetch(listing("1.2.0"))))
    assert snap.status == AVAILABLE and snap.release.version == "1.2.0"


def test_checks_are_weekly(tmp_path):
    first = Fetch(listing("1.2.0"))
    checked(make(tmp_path, first))
    later = Fetch(listing("1.3.0"))
    snap = checked(make(tmp_path, later, now=1000.0 + 6 * DAY))
    assert later.calls == 0 and snap.release.version == "1.2.0"
    snap = checked(make(tmp_path, later, now=1000.0 + 7 * DAY))
    assert later.calls == 1 and snap.release.version == "1.3.0"


def test_force_checks_anyway(tmp_path):
    checked(make(tmp_path, Fetch(listing("1.2.0"))))
    fetch = Fetch(listing("1.3.0"))
    assert checked(make(tmp_path, fetch, now=1001.0), force=True).release.version == "1.3.0"


def test_disabled_never_fetches(tmp_path):
    fetch = Fetch(listing("1.2.0"))
    u = make(tmp_path, fetch, enabled=False)
    assert checked(u, force=True).status == IDLE and fetch.calls == 0


def test_failed_check_is_quiet_and_retries_next_time(tmp_path):
    snap = checked(make(tmp_path, Fetch(UpdateError("offline"))))
    assert snap.status == IDLE and not (tmp_path / "update.json").exists()
    fetch = Fetch(listing("1.2.0"))
    checked(make(tmp_path, fetch))
    assert fetch.calls == 1


def test_a_bug_in_a_check_is_quiet_and_retries_next_time(tmp_path, monkeypatch):
    uncaught = []
    monkeypatch.setattr(threading, "excepthook", uncaught.append)
    u = make(tmp_path, Fetch(RuntimeError("bug")))
    snap = checked(u)
    assert uncaught == []
    assert snap.status == IDLE and u._state.last_check is None
    assert not (tmp_path / "update.json").exists()


def test_cached_result_is_offered_without_the_network(tmp_path):
    checked(make(tmp_path, Fetch(listing("1.2.0"))))
    u = make(tmp_path, Fetch(AssertionError("no network")), now=1000.0 + DAY)
    assert u.snapshot.status == AVAILABLE


def test_nothing_newer(tmp_path):
    assert checked(make(tmp_path, Fetch(listing("1.1.0")))).status == IDLE


def test_dismiss_hides_until_a_newer_version(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)
    u.dismiss()
    assert u.snapshot.status == IDLE
    assert make(tmp_path, Fetch(listing("1.2.0"))).snapshot.status == IDLE
    newer = make(tmp_path, Fetch(listing("1.2.0", "1.3.0")))
    assert checked(newer, force=True).release.version == "1.3.0"


def test_install_reports_progress_then_ready(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)
    seen = []

    def installer(release, progress):
        progress(0.5)
        seen.append(u.snapshot)

    u.install(installer)
    u.wait(5)
    assert seen[0].status == DOWNLOADING and seen[0].progress == 0.5
    assert u.snapshot.status == READY and u.snapshot.release.version == "1.2.0"


def test_failed_install_can_be_retried(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)

    def broken(release, progress):
        raise UpdateError("The download was interrupted.")

    u.install(broken)
    u.wait(5)
    assert u.snapshot.status == FAILED and "interrupted" in u.snapshot.message
    u.install(lambda release, progress: None)
    u.wait(5)
    assert u.snapshot.status == READY


def test_install_without_an_offer_does_nothing(tmp_path):
    u = make(tmp_path, Fetch(listing("1.1.0")))
    checked(u)
    u.install(lambda release, progress: None)
    u.wait(5)
    assert u.snapshot.status == IDLE


def test_turning_checks_off_hides_the_offer(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)
    u.set_enabled(False)
    assert u.snapshot.status == IDLE
    u.set_enabled(True)
    u.wait(5)
    assert u.snapshot.status == AVAILABLE


def test_for_program_from_source_is_none(tmp_path):
    assert for_program(GAME_WINDOWS, tmp_path, True) is None


def test_for_program_in_a_build(tmp_path, monkeypatch):
    exe = tmp_path / "Labyrinth.exe"
    exe.write_bytes(b"x")
    (tmp_path / "Labyrinth.exe.old").write_bytes(b"old")
    dump = tmp_path / "debug.json"
    monkeypatch.setenv(DEBUG_ENV, str(dump))
    monkeypatch.setattr(updater_module, "current_binary", lambda: exe)
    u = for_program(GAME_WINDOWS, tmp_path / "settings", True)
    assert u.target == exe and u.state_path == tmp_path / "settings" / "update.json"
    assert not (tmp_path / "Labyrinth.exe.old").exists()
    assert json.loads(dump.read_text(encoding="utf-8"))["binary"] == str(exe)


def test_install_proceeds_during_an_in_flight_check(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)
    assert u.snapshot.status == AVAILABLE

    blocking = BlockingFetch(listing("1.2.0"))
    u._fetch = blocking
    u.check(force=True)
    assert blocking.started.wait(5)

    u.install(lambda release, progress: None)
    u._install_thread.join(5)
    assert not u._install_thread.is_alive()
    assert u.snapshot.status == READY

    blocking.release_event.set()
    u._check_thread.join(5)
    assert not u._check_thread.is_alive()
    assert u.snapshot.status == READY and u.snapshot.release.version == "1.2.0"


def test_dismiss_during_an_in_flight_check_keeps_the_dismissal(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)

    blocking = BlockingFetch(listing("1.2.0"))
    u._fetch = blocking
    u.check(force=True)
    assert blocking.started.wait(5)

    u.dismiss()
    assert u.snapshot.status == IDLE

    blocking.release_event.set()
    u._check_thread.join(5)
    assert not u._check_thread.is_alive()
    assert u.snapshot.status == IDLE
    saved = json.loads((tmp_path / "update.json").read_text(encoding="utf-8"))
    assert saved["dismissed"] == "1.2.0"


def test_disabling_during_an_in_flight_check_keeps_it_hidden(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)

    blocking = BlockingFetch(listing("1.2.0"))
    u._fetch = blocking
    u.check(force=True)
    assert blocking.started.wait(5)

    u.set_enabled(False)
    assert u.snapshot.status == IDLE

    blocking.release_event.set()
    u._check_thread.join(5)
    assert not u._check_thread.is_alive()
    assert u.snapshot.status == IDLE


def test_unexpected_installer_exception_ends_in_failed_and_can_be_retried(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)

    def broken(release, progress):
        raise RuntimeError("boom")

    u.install(broken)
    u.wait(5)
    assert u.snapshot.status == FAILED
    assert u.snapshot.message == "The update could not be installed."

    u.install(lambda release, progress: None)
    u.wait(5)
    assert u.snapshot.status == READY


def test_a_newer_release_replaces_a_failed_one(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)

    def broken(release, progress):
        raise UpdateError("nope")

    u.install(broken)
    u.wait(5)
    assert u.snapshot.status == FAILED

    u._fetch = Fetch(listing("1.2.0", "1.3.0"))
    snap = checked(u, force=True)
    assert snap.status == AVAILABLE and snap.release.version == "1.3.0"


from labyrinth_update.notes import NoteEntry  # noqa: E402
from labyrinth_update.state import UpdateState, save  # noqa: E402


def test_a_check_stores_the_notes_of_every_newer_release(tmp_path):
    rels = listing("1.2.0", "1.3.0")
    rels[0]["body"] = "Two\n---\nsha"
    rels[1]["body"] = "Three"
    checked(make(tmp_path, Fetch(rels)))
    data = json.loads((tmp_path / "update.json").read_text(encoding="utf-8"))
    assert data["notes"] == [{"version": "1.3.0", "notes": "Three"},
                             {"version": "1.2.0", "notes": "Two"}]


def test_nothing_newer_keeps_the_stored_notes(tmp_path):
    save(tmp_path / "update.json", UpdateState(notes=(NoteEntry("1.1.0", "Now"),)))
    u = make(tmp_path, Fetch(listing("1.1.0")))
    checked(u)
    assert u._state.notes == (NoteEntry("1.1.0", "Now"),)


from labyrinth_update.whats_new import SHOW_RUNS  # noqa: E402


def test_first_run_records_the_running_version(tmp_path):
    u = make(tmp_path, Fetch(listing()))
    assert u.start_whats_new() is None
    data = json.loads((tmp_path / "update.json").read_text(encoding="utf-8"))
    assert data["last_run_version"] == "1.1.0"


def test_whats_new_shows_until_seen(tmp_path):
    save(tmp_path / "update.json",
         UpdateState(last_run_version="1.0.0", notes=(NoteEntry("1.1.0", "Eleven"),)))
    u = make(tmp_path, Fetch(listing()))
    assert u.start_whats_new().entries == (NoteEntry("1.1.0", "Eleven"),)
    u.mark_whats_new_seen()
    again = make(tmp_path, Fetch(listing()))
    assert again.start_whats_new() is None
    assert again.running_whats_new().entries == (NoteEntry("1.1.0", "Eleven"),)


def test_screensaver_run_counter_is_saved(tmp_path):
    save(tmp_path / "update.json", UpdateState(last_run_version="1.0.0"))
    for _ in range(SHOW_RUNS):
        u = make(tmp_path, Fetch(listing()))
        assert u.start_whats_new() is not None
        u.count_whats_new_run()
    assert make(tmp_path, Fetch(listing())).start_whats_new() is None


from labyrinth_update.updater import (CHECK_FAILED, CHECKING, UP_TO_DATE,  # noqa: E402
                                      CheckReport)


def asked(u):
    u.check_now()
    u.wait(5)
    return u.snapshot


def test_check_now_works_with_weekly_checks_off(tmp_path):
    fetch = Fetch(listing("1.2.0"))
    u = make(tmp_path, fetch, enabled=False)
    assert asked(u).status == AVAILABLE and fetch.calls == 1


def test_check_now_reports_up_to_date(tmp_path):
    u = make(tmp_path, Fetch(listing("1.1.0")))
    asked(u)
    assert u.check_report == CheckReport(UP_TO_DATE)


def test_only_check_now_reports_failures(tmp_path):
    u = make(tmp_path, Fetch(UpdateError("Could not reach the update server.")))
    checked(u)
    assert u.check_report == CheckReport()
    asked(u)
    assert u.check_report == CheckReport(CHECK_FAILED, "Could not reach the update server.")


def test_check_now_offers_a_dismissed_version_again(tmp_path):
    u = make(tmp_path, Fetch(listing("1.2.0")))
    checked(u)
    u.dismiss()
    assert asked(u).status == AVAILABLE and u._state.dismissed is None


def test_check_now_joins_a_check_in_flight(tmp_path):
    fetch = BlockingFetch(listing("1.1.0"))
    u = make(tmp_path, fetch)
    u.check()
    assert fetch.started.wait(5)
    u.check_now()
    assert u.check_report.status == CHECKING
    fetch.release_event.set()
    u.wait(5)
    assert fetch.calls == 1 and u.check_report.status == UP_TO_DATE


def test_check_now_after_a_check_finishes_starts_a_new_check(tmp_path):
    """A finished check must leave `_checking` clear so a later Check now is not mistaken
    for one still in flight (the bug this guards against used `is_alive()`, which can still
    read True for a moment after the worker leaves its last locked block)."""
    fetch = Fetch(listing("1.1.0"))
    u = make(tmp_path, fetch)
    checked(u)
    assert fetch.calls == 1
    u.check_now()
    u.wait(5)
    assert fetch.calls == 2 and u.check_report == CheckReport(UP_TO_DATE)


def test_check_now_preserves_run_state_fields(tmp_path):
    """A check that finds something newer must be a read-modify-write of the whole state:
    last_run_version, whats_new_runs and dismissed set before the check must still be in the
    saved update.json afterward, alongside the newly found release and notes."""
    save(tmp_path / "update.json",
         UpdateState(last_run_version="1.0.0", whats_new_runs=2, dismissed="0.9.0"))
    u = make(tmp_path, Fetch(listing("1.2.0")))
    asked(u)
    data = json.loads((tmp_path / "update.json").read_text(encoding="utf-8"))
    assert data["last_run_version"] == "1.0.0"
    assert data["whats_new_runs"] == 2
    assert data["dismissed"] == "0.9.0"
    assert data["found"]["version"] == "1.2.0"


def test_automatic_force_check_stays_off_after_check_now_with_weekly_checks_off(tmp_path):
    """Weekly checks off means automatic checks, forced or not, must never reach the
    network; only the user's own Check now may do that."""
    fetch = Fetch(listing("1.2.0"))
    u = make(tmp_path, fetch, enabled=False)
    asked(u)
    assert fetch.calls == 1
    u.check(force=True)
    u.wait(5)
    assert fetch.calls == 1
