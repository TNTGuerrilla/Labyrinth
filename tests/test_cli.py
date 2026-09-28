import pytest

from maze_saver.cli import Command, parse_args


@pytest.mark.parametrize("argv,expected", [
    ([], Command("config")),
    (["/s"], Command("saver")),
    (["/S"], Command("saver")),
    (["-s"], Command("saver")),
    (["/s", "junk"], Command("saver")),
    (["/c"], Command("config")),
    (["/c:1234"], Command("config", 1234)),
    (["/C", "99"], Command("config", 99)),
    (["/p", "5678"], Command("preview", 5678)),
    (["/p:5678"], Command("preview", 5678)),
    (["-P", "42"], Command("preview", 42)),
    (["/p"], Command("none")),
    (["/p", "abc"], Command("none")),
    (["/x"], Command("config")),
    (["hello"], Command("config")),
    (["--window"], Command("window")),
    (["/s", "--multiwindow"], Command("saver", multiwindow=True)),
    (["--multiwindow", "/s"], Command("saver", multiwindow=True)),
    (["/s", "--leads", "8"], Command("saver", leads=8)),
    (["--leads", "8", "/s"], Command("saver", leads=8)),
    (["--window", "--leads", "6"], Command("window", leads=6)),
    (["/s", "--leads", "abc"], Command("saver")),
    (["/s", "--leads"], Command("saver")),
    (["/s", "--leads", "0"], Command("saver")),
    (["/s", "--leads", "17"], Command("saver")),
    (["/s", "--multiwindow", "--leads", "4"], Command("saver", multiwindow=True, leads=4)),
])
def test_parse_args(argv, expected):
    assert parse_args(argv) == expected


def test_apply_update():
    sha = "ab" * 32
    c = parse_args(["--apply-update", r"C:\t\u.exe", r"C:\Windows\System32\Labyrinth.scr", sha])
    assert c.mode == "apply"
    assert c.update_args == (r"C:\t\u.exe", r"C:\Windows\System32\Labyrinth.scr", sha)
    assert parse_args(["--apply-update", "x"]).mode == "none"
