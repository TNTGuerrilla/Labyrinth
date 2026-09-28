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
