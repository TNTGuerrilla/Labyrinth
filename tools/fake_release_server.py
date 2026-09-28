"""Serves a fake GitHub releases list, for trying the in-app updater without publishing.

    .venv\\Scripts\\python tools\\fake_release_server.py --release labyrinth-v9.9.9=new\\Labyrinth.exe

Then start a build with LABYRINTH_UPDATE_URL=http://127.0.0.1:8765/releases. Debug builds of
the TV app already look at http://10.0.2.2:8765/releases, which is this PC as the Android
emulator sees it. The download links in the list use the host each client asked for (its
Host header), so they work from this PC and from the emulator alike.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def release_list(entries: list[tuple[str, Path]], base_url: str) -> list[dict]:
    """One release per (tag, file), shaped like the GitHub API's list."""
    releases = []
    for tag, path in entries:
        data = Path(path).read_bytes()
        releases.append({
            "tag_name": tag, "draft": False, "prerelease": False,
            "assets": [{"name": Path(path).name, "size": len(data),
                        "browser_download_url": f"{base_url}/files/{tag}/{Path(path).name}",
                        "digest": "sha256:" + hashlib.sha256(data).hexdigest()}],
        })
    return releases


_HOST = re.compile(r"[A-Za-z0-9.\-]+(:\d+)?|\[[0-9A-Fa-f:.]+\](:\d+)?")


def base_url(host: str | None, port: int) -> str:
    """http://<host> for a request's Host header, or this PC's loopback address when the
    header is missing or not a plain host[:port]."""
    if host and _HOST.fullmatch(host):
        return f"http://{host}"
    return f"http://127.0.0.1:{port}"


def make_handler(entries: list[tuple[str, Path]], port: int) -> type[BaseHTTPRequestHandler]:
    """A request handler serving /releases (built per request) and the release files."""
    files = {f"/files/{tag}/{Path(path).name}": Path(path) for tag, path in entries}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] == "/releases":
                base = base_url(self.headers.get("Host"), port)
                body = json.dumps(release_list(entries, base)).encode()
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

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", action="append", required=True, metavar="TAG=PATH")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    entries = []
    for item in args.release:
        tag, _, path = item.partition("=")
        entries.append((tag, Path(path)))
    print(f"Serving {len(entries)} release(s) at http://127.0.0.1:{args.port}/releases",
          flush=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(entries, args.port))
    server.serve_forever()


if __name__ == "__main__":
    main()
