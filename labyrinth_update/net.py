"""HTTPS requests and verified downloads for the updater."""
from __future__ import annotations

import hashlib
import http.client
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable, Optional

USER_AGENT = "Labyrinth-updater"
CHUNK = 64 * 1024
MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024  # far above any release file; stops an endless stream
# The Linux build carries its own OpenSSL, which looks for certificates where Ubuntu keeps
# them. Other distributions keep the bundle in one of these places instead.
LINUX_CA_FILES = ("/etc/ssl/certs/ca-certificates.crt", "/etc/pki/tls/certs/ca-bundle.crt",
                  "/etc/ssl/ca-bundle.pem", "/etc/ssl/cert.pem")

Progress = Callable[[float], None]


class UpdateError(Exception):
    """A check, download or install that failed. str() is a sentence for the user."""


def ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    if sys.platform.startswith("linux"):
        for path in LINUX_CA_FILES:
            if os.path.isfile(path):
                try:
                    context.load_verify_locations(cafile=path)
                    break
                except ssl.SSLError:
                    continue
    return context


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follows redirects, except from https to anything else. GitHub sends release files
    from objects.githubusercontent.com, so https to https must keep working."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if (urllib.parse.urlsplit(req.full_url).scheme.lower() == "https"
                and urllib.parse.urlsplit(newurl).scheme.lower() != "https"):
            raise urllib.error.HTTPError(newurl, code, "Refused a redirect away from https",
                                         headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_url(url: str, accept: str, timeout: float):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context()),
                                         SafeRedirectHandler())
    try:
        return opener.open(request, timeout=timeout)
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:
        raise UpdateError("Could not reach the update server.") from exc


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _remove(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def download(url: str, dest: Path, sha256: str, on_progress: Optional[Progress] = None,
             timeout: float = 30) -> None:
    """Save url to dest and check its SHA-256. On any failure dest is removed and
    UpdateError is raised, so a partial or wrong file is never left behind. A file larger
    than MAX_DOWNLOAD_BYTES is refused."""
    digest = hashlib.sha256()
    response = open_url(url, "application/octet-stream", timeout)
    try:
        with response, open(dest, "wb") as out:
            total = int(response.headers.get("Content-Length") or 0)
            done = 0
            too_large = total > MAX_DOWNLOAD_BYTES
            while not too_large:
                chunk = response.read(CHUNK)
                if not chunk:
                    break
                if done + len(chunk) > MAX_DOWNLOAD_BYTES:
                    too_large = True
                    break
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if on_progress is not None and total > 0:
                    on_progress(min(1.0, done / total))
    except PermissionError as exc:
        _remove(dest)
        raise UpdateError(f"Can't write to {dest.parent}.") from exc
    except (OSError, http.client.HTTPException, ValueError) as exc:
        _remove(dest)
        raise UpdateError("The download was interrupted.") from exc
    if too_large:
        _remove(dest)
        raise UpdateError("The download was too large to be an update.")
    if done < total and total > 0:
        _remove(dest)
        raise UpdateError("The download was interrupted.")
    if digest.hexdigest() != sha256.lower():
        _remove(dest)
        raise UpdateError("The download did not match its published checksum.")
