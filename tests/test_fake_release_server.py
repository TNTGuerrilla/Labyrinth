import hashlib
import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from labyrinth_update.releases import GAME_WINDOWS, URL_ENV, newest
from tools.fake_release_server import base_url, make_handler, release_list


@pytest.fixture(autouse=True)
def pointed_at_the_fake_server(monkeypatch):
    """Desktop builds only take links to this PC from the fake server while URL_ENV is set."""
    monkeypatch.setenv(URL_ENV, "http://127.0.0.1:8765/releases")


def test_release_list_looks_like_github(tmp_path):
    exe = tmp_path / "Labyrinth.exe"
    exe.write_bytes(b"new build")
    listing = release_list([("labyrinth-v9.9.9", exe)], "http://127.0.0.1:8765")
    found = newest(listing, GAME_WINDOWS, "1.0.0")
    assert found.version == "9.9.9"
    assert found.url == "http://127.0.0.1:8765/files/labyrinth-v9.9.9/Labyrinth.exe"
    assert found.sha256 == hashlib.sha256(b"new build").hexdigest()


def test_base_url_uses_the_host_the_client_asked_for():
    assert base_url("10.0.2.2:8765", 8765) == "http://10.0.2.2:8765"
    assert base_url(None, 8765) == "http://127.0.0.1:8765"
    assert base_url("", 8765) == "http://127.0.0.1:8765"
    assert base_url("bad host/x", 8765) == "http://127.0.0.1:8765"


@pytest.fixture
def fake_server(tmp_path):
    exe = tmp_path / "Labyrinth.exe"
    exe.write_bytes(b"new build")
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 make_handler([("labyrinth-v9.9.9", exe)], 8765))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()
    thread.join(5)


def get(port, path, host):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        conn.request("GET", path, headers={"Host": host})
        response = conn.getresponse()
        return response.status, response.getheader("Content-Type"), response.read()
    finally:
        conn.close()


def test_listing_links_use_the_request_host(fake_server):
    status, kind, body = get(fake_server, "/releases?per_page=100", "10.0.2.2:8765")
    assert status == 200 and kind == "application/json"
    # 10.0.2.2 is how the TV emulator reaches this PC, so the TV's updater checks this link.
    asset = json.loads(body)[0]["assets"][0]
    assert asset["browser_download_url"] == (
        "http://10.0.2.2:8765/files/labyrinth-v9.9.9/Labyrinth.exe")
    status, kind, body = get(fake_server, "/files/labyrinth-v9.9.9/Labyrinth.exe",
                             "10.0.2.2:8765")
    assert status == 200 and kind == "application/octet-stream" and body == b"new build"


from labyrinth_update.notes import NoteEntry, collect_notes  # noqa: E402
from tools.fake_release_server import parse_notes_arg  # noqa: E402


def test_notes_become_release_bodies(tmp_path):
    exe = tmp_path / "Labyrinth.exe"
    exe.write_bytes(b"new build")
    listing = release_list([("labyrinth-v9.9.9", exe)], "http://127.0.0.1:8765",
                           {"labyrinth-v9.9.9": "Nine\n---\nsha", "labyrinth-v9.9.8": "Eight"})
    assert listing[0]["body"] == "Nine\n---\nsha"
    assert collect_notes(listing, GAME_WINDOWS, "1.0.0", "9.9.9") == [
        NoteEntry("9.9.9", "Nine"), NoteEntry("9.9.8", "Eight")]
    assert newest(listing, GAME_WINDOWS, "1.0.0").version == "9.9.9"
    assert newest(listing, GAME_WINDOWS, "9.9.9") is None  # a notes-only release is never offered


def test_parse_notes_arg():
    assert parse_notes_arg("labyrinth-v9.9.9=## New\\n- Faster") == (
        "labyrinth-v9.9.9", "## New\n- Faster")
    assert parse_notes_arg("t=a=b") == ("t", "a=b")


def test_one_connection_serves_several_requests(fake_server):
    # The Android emulator's network lost responses from a server that closed each connection
    # straight after writing; HTTP/1.1 keeps it open for the client's next request instead.
    conn = http.client.HTTPConnection("127.0.0.1", fake_server, timeout=5)
    try:
        for path in ("/releases", "/files/labyrinth-v9.9.9/Labyrinth.exe", "/releases"):
            conn.request("GET", path, headers={"Host": "10.0.2.2:8765"})
            response = conn.getresponse()
            body = response.read()
            assert response.status == 200 and response.version == 11
            assert int(response.getheader("Content-Length")) == len(body)
            assert not response.will_close
    finally:
        conn.close()
