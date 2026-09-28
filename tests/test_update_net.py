import hashlib

import pytest

from labyrinth_update.net import UpdateError, download, file_sha256, open_url

BODY = b"new program " * 5000
SHA = hashlib.sha256(BODY).hexdigest()


def test_download_verifies_and_reports_progress(serve, tmp_path):
    server = serve({"/f": BODY})
    seen = []
    dest = tmp_path / "f.new"
    download(server.url("/f"), dest, SHA, seen.append)
    assert dest.read_bytes() == BODY
    assert seen and seen[-1] == 1.0 and seen == sorted(seen)
    assert file_sha256(dest) == SHA


def test_uppercase_checksum_is_accepted(serve, tmp_path):
    server = serve({"/f": BODY})
    download(server.url("/f"), tmp_path / "f", SHA.upper())


def test_checksum_mismatch_removes_the_file(serve, tmp_path):
    server = serve({"/f": BODY})
    dest = tmp_path / "f.new"
    with pytest.raises(UpdateError, match="checksum"):
        download(server.url("/f"), dest, "0" * 64)
    assert not dest.exists()


def test_interrupted_download_removes_the_file(serve, tmp_path):
    server = serve({"/f": (BODY[:1000], len(BODY))})
    dest = tmp_path / "f.new"
    with pytest.raises(UpdateError, match="interrupted"):
        download(server.url("/f"), dest, SHA, timeout=5)
    assert not dest.exists()


def test_missing_file_is_an_update_error(serve, tmp_path):
    server = serve({})
    with pytest.raises(UpdateError, match="reach"):
        download(server.url("/nope"), tmp_path / "x", SHA)


def test_unreachable_server():
    with pytest.raises(UpdateError):
        open_url("http://127.0.0.1:9/", "*/*", timeout=2)
