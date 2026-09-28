import json

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
