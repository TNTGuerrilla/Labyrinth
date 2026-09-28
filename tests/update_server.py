"""A local HTTP server for updater tests: serves fixed bytes at fixed paths."""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Server:
    def __init__(self, routes: dict):
        table = routes

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                entry = table.get(self.path)
                if entry is None:
                    self.send_error(404)
                    return
                body, length = entry if isinstance(entry, tuple) else (entry, len(entry))
                self.send_response(200)
                self.send_header("Content-Length", str(length))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}{path}"

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
