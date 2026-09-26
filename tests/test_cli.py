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
])
def test_parse_args(argv, expected):
    assert parse_args(argv) == expected
