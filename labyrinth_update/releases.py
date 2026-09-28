"""Which releases exist on GitHub, and which one is newest for a product."""
from __future__ import annotations

import http.client
import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Optional

from .net import UpdateError, open_url
from .version import parse_version

API_URL = "https://api.github.com/repos/TNTGuerrilla/Labyrinth/releases?per_page=100"
URL_ENV = "LABYRINTH_UPDATE_URL"  # points the updater at a test server
MAX_LIST_BYTES = 8_000_000
_SHA256 = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class Product:
    name: str  # shown to the user
    key: str  # key in versions.json
    tag_prefix: str
    asset: str  # release file name; {version} is filled in


GAME_WINDOWS = Product("Labyrinth", "game", "labyrinth-v", "Labyrinth.exe")
GAME_LINUX = Product("Labyrinth", "game", "labyrinth-v",
                     "Labyrinth-{version}-linux-x86_64.tar.gz")
SCREENSAVER = Product("Labyrinth Screensaver", "screensaver", "labyrinth-screensaver-v",
                      "Labyrinth.scr")


def game_product() -> Product:
    return GAME_WINDOWS if sys.platform == "win32" else GAME_LINUX


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    sha256: str  # lowercase hex


def _sha256(asset: dict) -> Optional[str]:
    digest = asset.get("digest")
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        return None
    value = digest[len("sha256:"):].lower()
    return value if _SHA256.fullmatch(value) else None


def _asset(release: dict, name: str) -> Optional[dict]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        return None
    return next((a for a in assets if isinstance(a, dict) and a.get("name") == name), None)


def newest(releases: Any, product: Product, current: str) -> Optional[Release]:
    """The highest release of `product` newer than `current` whose file has a published
    SHA-256. Drafts, pre-releases and other products' tags are ignored. `releases` is the
    parsed GitHub API list and is untrusted, so any shape is handled."""
    best_version = parse_version(current)
    if best_version is None or not isinstance(releases, list):
        return None
    best = None
    for release in releases:
        if not isinstance(release, dict) or release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name")
        if not isinstance(tag, str) or not tag.startswith(product.tag_prefix):
            continue
        text = tag[len(product.tag_prefix):]
        version = parse_version(text)
        if version is None or version <= best_version:
            continue
        asset = _asset(release, product.asset.format(version=text))
        if asset is None:
            continue
        url = asset.get("browser_download_url")
        sha = _sha256(asset)
        if not isinstance(url, str) or sha is None:
            continue
        best, best_version = Release(text, url, sha), version
    return best


def releases_url() -> str:
    return os.environ.get(URL_ENV) or API_URL


def fetch_releases(timeout: float = 15) -> Any:
    """The parsed release list. Raises UpdateError if it cannot be fetched or read."""
    response = open_url(releases_url(), "application/vnd.github+json", timeout)
    try:
        with response:
            return json.loads(response.read(MAX_LIST_BYTES).decode("utf-8"))
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise UpdateError("Could not read the list of releases.") from exc
