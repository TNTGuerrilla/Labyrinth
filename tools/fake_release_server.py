"""Serves a fake GitHub releases list, for trying the in-app updater without publishing.

    .venv\\Scripts\\python tools\\fake_release_server.py --release labyrinth-v9.9.9=new\\Labyrinth.exe

Then start a build with LABYRINTH_UPDATE_URL=http://127.0.0.1:8765/releases. Debug builds of
the TV app already look at http://10.0.2.2:8765/releases, which is this PC as the Android
emulator sees it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", action="append", required=True, metavar="TAG=PATH")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    entries = []
    for item in args.release:
        tag, _, path = item.partition("=")
        entries.append((tag, Path(path)))
    base = f"http://127.0.0.1:{args.port}"
    listing = json.dumps(release_list(entries, base)).encode()
    files = {f"/files/{tag}/{path.name}": path for tag, path in entries}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] == "/releases":
                body = listing
            elif self.path in files:
                body = files[self.path].read_bytes()
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    print(f"Serving {len(entries)} release(s) at {base}/releases", flush=True)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
