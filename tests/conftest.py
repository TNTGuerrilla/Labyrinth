import os

import pytest

# Headless pygame for tests that create surfaces; silence the import banner.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from tests.update_server import Server  # noqa: E402


@pytest.fixture
def serve():
    """serve({path: bytes}) starts a local HTTP server; it stops after the test."""
    servers = []

    def start(routes):
        server = Server(routes)
        servers.append(server)
        return server

    yield start
    for server in servers:
        server.close()
