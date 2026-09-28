from labyrinth_update.version import current_binary, parse_version, running_version


def test_parse_version():
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version(" 10.0.12 ") == (10, 0, 12)
    for bad in ("1.2", "1.2.3.4", "v1.2.3", "1.2.x", "", None, 3):
        assert parse_version(bad) is None


def test_versions_compare_numerically():
    assert parse_version("1.10.0") > parse_version("1.9.9")


def test_running_version(tmp_path):
    f = tmp_path / "versions.json"
    f.write_text('{"game": "1.1.0", "screensaver": "bad"}', encoding="utf-8")
    assert running_version("game", f) == "1.1.0"
    assert running_version("screensaver", f) is None
    assert running_version("tv", f) is None
    assert running_version("game", tmp_path / "missing.json") is None


def test_running_version_from_source_reads_the_repo_file():
    assert running_version("game") is not None


def test_current_binary(tmp_path):
    exe = tmp_path / "Labyrinth.exe"
    exe.write_bytes(b"x")
    assert current_binary(str(exe), built=True) == exe.resolve()
    assert current_binary(str(exe), built=False) is None
    assert current_binary(str(tmp_path / "gone.exe"), built=True) is None
    assert current_binary("", built=True) is None


def test_source_runs_have_no_binary():
    assert current_binary() is None
