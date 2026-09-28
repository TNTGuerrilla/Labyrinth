import json

from labyrinth_update.releases import (GAME_LINUX, GAME_WINDOWS, SCREENSAVER, URL_ENV, Release,
                                       fetch_releases, newest)

SHA = "ab" * 32


def asset(name, sha=SHA):
    a = {"name": name, "browser_download_url": f"https://example.test/{name}"}
    if sha is not None:
        a["digest"] = f"sha256:{sha}"
    return a


def release(tag, *assets, draft=False, prerelease=False):
    return {"tag_name": tag, "draft": draft, "prerelease": prerelease, "assets": list(assets)}


LIST = [
    release("labyrinth-v1.1.0", asset("Labyrinth.exe"),
            asset("Labyrinth-1.1.0-linux-x86_64.tar.gz")),
    release("labyrinth-v1.3.0", asset("Labyrinth.exe"), draft=True),
    release("labyrinth-v1.4.0", asset("Labyrinth.exe"), prerelease=True),
    release("labyrinth-v1.2.0", asset("Labyrinth.exe"),
            asset("Labyrinth-1.2.0-linux-x86_64.tar.gz")),
    release("labyrinth-screensaver-v2.0.0", asset("Labyrinth.scr")),
    release("labyrinth-tv-v9.0.0", asset("LabyrinthTV.apk")),
]


def test_newest_game_release():
    assert newest(LIST, GAME_WINDOWS, "1.1.0") == Release(
        "1.2.0", "https://example.test/Labyrinth.exe", SHA)
    assert newest(LIST, GAME_LINUX, "1.1.0").url.endswith("Labyrinth-1.2.0-linux-x86_64.tar.gz")


def test_nothing_newer():
    assert newest(LIST, GAME_WINDOWS, "1.2.0") is None
    assert newest(LIST, GAME_WINDOWS, "5.0.0") is None


def test_products_do_not_see_each_others_tags():
    assert newest(LIST, SCREENSAVER, "1.0.1").version == "2.0.0"
    assert newest(LIST, GAME_WINDOWS, "0.0.1").version == "1.2.0"


def test_version_order_is_numeric():
    rels = [release("labyrinth-v1.9.0", asset("Labyrinth.exe")),
            release("labyrinth-v1.10.0", asset("Labyrinth.exe"))]
    assert newest(rels, GAME_WINDOWS, "1.0.0").version == "1.10.0"


def test_releases_without_a_checksum_or_the_file_are_skipped():
    rels = [release("labyrinth-v1.5.0", asset("Labyrinth.exe", sha=None)),
            release("labyrinth-v1.6.0", asset("Labyrinth.exe", sha="zz")),
            release("labyrinth-v1.7.0", asset("Other.exe")),
            release("labyrinth-v1.4.0", asset("Labyrinth.exe"))]
    assert newest(rels, GAME_WINDOWS, "1.0.0").version == "1.4.0"


def test_untrusted_shapes_are_ignored():
    junk_lists = (None, {}, "x", [None, 3, {"tag_name": 5},
                                  {"tag_name": "labyrinth-v2.0.0", "assets": "x"},
                                  {"tag_name": "labyrinth-v2.0.0", "assets": [None, 4]}])
    for junk in junk_lists:
        assert newest(junk, GAME_WINDOWS, "1.0.0") is None
    assert newest(LIST, GAME_WINDOWS, "not a version") is None


def test_digest_is_lowercased():
    rels = [release("labyrinth-v2.0.0", asset("Labyrinth.exe", sha="AB" * 32))]
    assert newest(rels, GAME_WINDOWS, "1.0.0").sha256 == SHA


def test_fetch_uses_the_override_url(serve, monkeypatch):
    server = serve({"/releases": json.dumps(LIST).encode()})
    monkeypatch.setenv(URL_ENV, server.url("/releases"))
    assert fetch_releases() == LIST
