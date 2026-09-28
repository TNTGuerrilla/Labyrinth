import hashlib

from labyrinth_update.releases import GAME_WINDOWS, newest
from tools.fake_release_server import release_list


def test_release_list_looks_like_github(tmp_path):
    exe = tmp_path / "Labyrinth.exe"
    exe.write_bytes(b"new build")
    listing = release_list([("labyrinth-v9.9.9", exe)], "http://127.0.0.1:8765")
    found = newest(listing, GAME_WINDOWS, "1.0.0")
    assert found.version == "9.9.9"
    assert found.url == "http://127.0.0.1:8765/files/labyrinth-v9.9.9/Labyrinth.exe"
    assert found.sha256 == hashlib.sha256(b"new build").hexdigest()
