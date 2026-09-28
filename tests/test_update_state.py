import json

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
