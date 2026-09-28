from maze_saver.icon import ICON_PATH, load_icon


def test_icon_file_ships_with_the_package():
    assert ICON_PATH.is_file()


def test_icon_loads_at_full_size():
    icon = load_icon()
    assert icon is not None
    assert icon.get_size() == (256, 256)


def test_missing_icon_gives_none(monkeypatch, tmp_path):
    monkeypatch.setattr("maze_saver.icon.ICON_PATH", tmp_path / "gone.png")
    assert load_icon() is None
