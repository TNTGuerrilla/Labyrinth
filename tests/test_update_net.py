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


def test_download_larger_than_the_cap_by_its_length_is_refused(serve, tmp_path, monkeypatch):
    from labyrinth_update import net
    monkeypatch.setattr(net, "MAX_DOWNLOAD_BYTES", len(BODY) - 1)
    server = serve({"/f": BODY})
    dest = tmp_path / "f.new"
    with pytest.raises(UpdateError, match="too large"):
        download(server.url("/f"), dest, SHA)
    assert not dest.exists()


class _Unsized:
    """A response with no Content-Length that sends `chunks`."""

    def __init__(self, chunks):
        self.headers = {}
        self._chunks = list(chunks)

    def read(self, size):
        return self._chunks.pop(0) if self._chunks else b""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_download_larger_than_the_cap_by_its_bytes_is_refused(tmp_path, monkeypatch):
    from labyrinth_update import net
    monkeypatch.setattr(net, "MAX_DOWNLOAD_BYTES", 100)
    monkeypatch.setattr(net, "open_url", lambda *a, **k: _Unsized([b"x" * 60, b"x" * 60]))
    dest = tmp_path / "f.new"
    with pytest.raises(UpdateError, match="too large"):
        download("https://github.com/f", dest, SHA)
    assert not dest.exists()


def test_the_download_cap_is_sane():
    from labyrinth_update import net
    assert 100 * 1024 * 1024 <= net.MAX_DOWNLOAD_BYTES <= 1024 * 1024 * 1024


def _redirect(source, target):
    import email.message
    import urllib.request

    from labyrinth_update import net
    handler = net.SafeRedirectHandler()
    return handler.redirect_request(urllib.request.Request(source), None, 302, "Found",
                                    email.message.Message(), target)


def test_https_redirects_to_https_are_followed():
    new = _redirect("https://github.com/a", "https://objects.githubusercontent.com/b")
    assert new.full_url == "https://objects.githubusercontent.com/b"


def test_https_redirects_to_http_are_refused():
    import urllib.error
    with pytest.raises(urllib.error.HTTPError):
        _redirect("https://github.com/a", "http://objects.githubusercontent.com/b")


def test_http_redirects_still_work_for_the_local_test_server():
    assert _redirect("http://127.0.0.1:8765/a", "http://127.0.0.1:8765/b") is not None


def test_open_url_uses_the_safe_redirect_handler(monkeypatch):
    from labyrinth_update import net
    seen = []
    real = net.urllib.request.build_opener

    def spy(*handlers):
        seen.extend(handlers)
        return real(*handlers)

    monkeypatch.setattr(net.urllib.request, "build_opener", spy)
    with pytest.raises(UpdateError):
        open_url("http://127.0.0.1:9/", "*/*", timeout=2)
    assert any(isinstance(h, net.SafeRedirectHandler) for h in seen)
