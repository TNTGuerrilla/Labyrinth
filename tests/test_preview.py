from maze_saver.preview import claim_name, is_superseded, make_token, preview_should_run


def test_runs_while_parent_and_child_live_and_not_superseded():
    assert preview_should_run(parent_alive=True, child_alive=True, superseded=False)


def test_stops_when_the_parent_is_gone():
    assert not preview_should_run(parent_alive=False, child_alive=True, superseded=False)


def test_stops_when_windows_destroys_the_child():
    assert not preview_should_run(parent_alive=True, child_alive=False, superseded=False)


def test_stops_when_a_newer_preview_took_over():
    assert not preview_should_run(parent_alive=True, child_alive=True, superseded=True)


def test_claim_name_is_per_parent_window():
    assert claim_name(0x1234) == "Local\\LabyrinthScreensaverPreview-4660"
    assert claim_name(1) != claim_name(2)


def test_tokens_are_nonzero_and_distinct_per_process_and_serial():
    tokens = {make_token(pid, serial) for pid in (4, 5, 0xFFFFFFFF) for serial in (1, 2, 0xFFFFFFFF)}
    assert len(tokens) == 9
    assert 0 not in tokens
    assert all(0 < t < 2 ** 64 for t in tokens)


def test_superseded_only_when_someone_else_owns_the_slot():
    mine = make_token(10, 1)
    assert not is_superseded(mine, mine)
    assert is_superseded(mine, make_token(11, 1))
    assert is_superseded(mine, make_token(10, 2))


def test_an_empty_slot_does_not_supersede():
    # A zeroed mapping (nobody claimed, or the claim was never written) must not end a preview.
    assert not is_superseded(make_token(10, 1), 0)
