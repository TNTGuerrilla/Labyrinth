"""Serves a fake GitHub releases list, for trying the in-app updater without publishing.

    .venv\\Scripts\\python tools\\fake_release_server.py --release labyrinth-v9.9.9=new\\Labyrinth.exe
    --notes "labyrinth-v9.9.9=## New\\n- Faster"

Then start a build with LABYRINTH_UPDATE_URL=http://127.0.0.1:8765/releases. Debug builds of
the TV app already look at http://10.0.2.2:8765/releases, which is this PC as the Android
emulator sees it. The download links in the list use the host each client asked for (its
Host header), so they work from this PC and from the emulator alike. The --notes option sets
a release's notes (\\n is a line break).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def release_list(entries: list[tuple[str, Path]], base_url: str,
                 notes: dict[str, str] | None = None) -> list[dict]:
    """One release per (tag, file), shaped like the GitHub API's list, each with its notes
    as the body. A notes tag without a file becomes a release with no files: it is never
    offered, but its notes are collected like a skipped version's."""
    notes = notes or {}
    releases = []
    for tag, path in entries:
        data = Path(path).read_bytes()
        releases.append({
            "tag_name": tag, "draft": False, "prerelease": False, "body": notes.get(tag, ""),
            "assets": [{"name": Path(path).name, "size": len(data),
                        "browser_download_url": f"{base_url}/files/{tag}/{Path(path).name}",
                        "digest": "sha256:" + hashlib.sha256(data).hexdigest()}],
        })
    with_files = {tag for tag, _ in entries}
    for tag, text in notes.items():
        if tag not in with_files:
            releases.append({"tag_name": tag, "draft": False, "prerelease": False,
                             "body": text, "assets": []})
    return releases


def parse_notes_arg(item: str) -> tuple[str, str]:
    """TAG=TEXT from the command line; a literal \\n in TEXT becomes a line break."""
    tag, _, text = item.partition("=")
    return tag, text.replace("\\n", "\n")


_HOST = re.compile(r"[A-Za-z0-9.\-]+(:\d+)?|\[[0-9A-Fa-f:.]+\](:\d+)?")


def base_url(host: str | None, port: int) -> str:
    """http://<host> for a request's Host header, or this PC's loopback address when the
    header is missing or not a plain host[:port]."""
    if host and _HOST.fullmatch(host):
        return f"http://{host}"
    return f"http://127.0.0.1:{port}"


def make_handler(entries: list[tuple[str, Path]], port: int,
                 notes: dict[str, str] | None = None) -> type[BaseHTTPRequestHandler]:
    """A request handler serving /releases (built per request) and the release files."""
    files = {f"/files/{tag}/{Path(path).name}": Path(path) for tag, path in entries}

    class Handler(BaseHTTPRequestHandler):
        # HTTP/1.1 keeps each connection open for the client's next request (every response
        # has a Content-Length). The Android emulator's network lost responses from a server
        # that closed the connection straight after writing, even with "Connection: close".
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            if self.path.split("?")[0] == "/releases":
                base = base_url(self.headers.get("Host"), port)
                body = json.dumps(release_list(entries, base, notes)).encode()
                kind = "application/json"
            elif self.path in files:
                body = files[self.path].read_bytes()
                kind = "application/octet-stream"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", action="append", required=True, metavar="TAG=PATH")
    parser.add_argument("--notes", action="append", default=[], metavar="TAG=TEXT")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    entries = []
    for item in args.release:
        tag, _, path = item.partition("=")
        entries.append((tag, Path(path)))
    notes = dict(parse_notes_arg(item) for item in args.notes)
    print(f"Serving {len(entries)} release(s) and {len(notes)} set(s) of notes at "
          f"http://127.0.0.1:{args.port}/releases", flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(entries, args.port, notes))
    server.serve_forever()


if __name__ == "__main__":
    main()
