import json
from pathlib import Path

import pytest

from labyrinth_update.releases import Release
from labyrinth_update.state import CHECK_INTERVAL, UpdateState, is_due, load, save, visible

REL = Release("1.2.0", "https://example.test/Labyrinth.exe", "ab" * 32)


def test_round_trip(tmp_path):
    path = tmp_path / "sub" / "update.json"
    state = UpdateState(1000.0, REL, "1.1.5")
    save(path, state)
    assert load(path) == state


def test_missing_or_damaged_file(tmp_path):
    assert load(tmp_path / "none.json") == UpdateState()
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load(bad) == UpdateState()
    bad.write_text('{"last_check": "x", "found": {"version": "nope"}, "dismissed": 4}',
                   encoding="utf-8")
    assert load(bad) == UpdateState()
    bad.write_text("[1, 2]", encoding="utf-8")
    assert load(bad) == UpdateState()


def test_is_due():
    assert is_due(UpdateState(), 5.0)
    assert not is_due(UpdateState(last_check=100.0), 100.0 + CHECK_INTERVAL - 1)
    assert is_due(UpdateState(last_check=100.0), 100.0 + CHECK_INTERVAL)
    assert is_due(UpdateState(last_check=100.0), 50.0)  # the clock went back


def test_visible():
    assert visible(UpdateState(found=REL), "1.1.0") == REL
    assert visible(UpdateState(found=REL, dismissed="1.2.0"), "1.1.0") is None
    assert visible(UpdateState(found=REL, dismissed="1.1.9"), "1.1.0") == REL
    assert visible(UpdateState(found=REL), "1.2.0") is None  # already running it
    assert visible(UpdateState(), "1.1.0") is None


def test_save_writes_a_temp_file_then_replaces_the_target(tmp_path, monkeypatch):
    import os

    from labyrinth_update import state as state_module

    path = tmp_path / "update.json"
    calls = []
    real_replace = os.replace

    def fake_replace(src, dst):
        calls.append((Path(src), Path(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(state_module.os, "replace", fake_replace)
    state = UpdateState(1000.0, REL, "1.1.5")
    save(path, state)
    assert len(calls) == 1
    tmp, dst = calls[0]
    assert dst == path
    assert tmp.parent == path.parent and tmp != path
    assert tmp.name == f"update.json.{os.getpid()}.tmp"  # per-process: no cross-process clash
    assert not tmp.exists()  # replaced onto the target, nothing left behind
    assert list(tmp_path.iterdir()) == [path]
    assert load(path) == state


def test_save_removes_the_temp_file_if_the_replace_fails(tmp_path, monkeypatch):
    from labyrinth_update import state as state_module

    path = tmp_path / "update.json"

    def fake_replace(src, dst):
        raise OSError("locked")

    monkeypatch.setattr(state_module.os, "replace", fake_replace)
    with pytest.raises(OSError):
        save(path, UpdateState(1000.0, REL, "1.1.5"))
    assert list(tmp_path.iterdir()) == []  # nothing left behind after the failure


def test_found_with_a_bad_sha256_is_dropped(tmp_path):
    path = tmp_path / "update.json"
    for bad in ("ab" * 31, "AB" * 32, "zz" * 32, "ab" * 33, ""):
        path.write_text(json.dumps({"last_check": 5.0, "dismissed": None, "found": {
            "version": "1.2.0", "url": "https://example.test/x", "sha256": bad}}),
            encoding="utf-8")
        assert load(path) == UpdateState(last_check=5.0), bad


import json  # noqa: E402

from labyrinth_update.notes import NoteEntry  # noqa: E402

NOTES = (NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two"))


def test_notes_and_seen_state_round_trip(tmp_path):
    path = tmp_path / "update.json"
    state = UpdateState(1000.0, REL, None, NOTES, "1.1.0", 2)
    save(path, state)
    assert load(path) == state


def test_stored_notes_use_the_contract_format(tmp_path):
    path = tmp_path / "update.json"
    save(path, UpdateState(notes=NOTES, last_run_version="1.1.0", whats_new_runs=1))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["notes"] == [{"version": "1.3.0", "notes": "Three"},
                             {"version": "1.2.0", "notes": "Two"}]
    assert data["last_run_version"] == "1.1.0" and data["whats_new_runs"] == 1


def test_damaged_notes_and_seen_fields_are_ignored(tmp_path):
    path = tmp_path / "update.json"
    path.write_text(json.dumps({
        "notes": [{"version": "x", "notes": "a"}, {"version": "1.2.0"}, 5,
                  {"version": "1.1.0", "notes": "ok"}],
        "last_run_version": "nope", "whats_new_runs": -3}), encoding="utf-8")
    state = load(path)
    assert state.notes == (NoteEntry("1.1.0", "ok"),)
    assert state.last_run_version is None and state.whats_new_runs == 0
    path.write_text('{"last_check": 5, "found": null, "dismissed": null}', encoding="utf-8")
    assert load(path) == UpdateState(last_check=5.0)  # a file from before this feature


def test_save_removes_temp_files_left_by_killed_runs(tmp_path):
    import os
    import time

    path = tmp_path / "update.json"
    old = tmp_path / "update.json.1234.tmp"
    fresh = tmp_path / "update.json.5678.tmp"  # another run may be saving right now
    other = tmp_path / "config.json.1234.tmp"
    for f in (old, fresh, other):
        f.write_text("{}")
    hours_ago = time.time() - 2 * 3600
    os.utime(old, (hours_ago, hours_ago))
    os.utime(other, (hours_ago, hours_ago))
    save(path, UpdateState(1000.0, REL, "1.1.5"))
    assert not old.exists()
    assert fresh.exists() and other.exists()
    assert load(path) == UpdateState(1000.0, REL, "1.1.5")


def test_a_temp_file_that_cannot_be_removed_does_not_stop_the_save(tmp_path, monkeypatch):
    import os
    import time

    path = tmp_path / "update.json"
    old = tmp_path / "update.json.1234.tmp"
    old.write_text("{}")
    hours_ago = time.time() - 2 * 3600
    os.utime(old, (hours_ago, hours_ago))
    real_unlink = Path.unlink

    def locked(self, missing_ok=False):
        if self == old:
            raise PermissionError("locked")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", locked)
    save(path, UpdateState(1000.0, REL, "1.1.5"))
    assert load(path) == UpdateState(1000.0, REL, "1.1.5")
