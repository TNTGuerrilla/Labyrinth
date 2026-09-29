import hashlib
import io
import os
import sys
import tarfile
import time
from pathlib import Path

import pytest

from labyrinth_update import APPLY_FLAG, install
from labyrinth_update.install import (STAGED_NAME, apply_update, can_write, cleanup_old,
                                      extract_linux_binary, install_game, install_screensaver,
                                      new_path, relaunch, swap)
from labyrinth_update.net import UpdateError
from labyrinth_update.releases import Release


def sha(data):
    return hashlib.sha256(data).hexdigest()


def program(folder, name="Labyrinth.exe", data=b"old"):
    path = folder / name
    path.write_bytes(data)
    return path


def tarball(binary=b"new linux", version="1.2.0", include=True):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        folder = f"Labyrinth-{version}-linux-x86_64"
        files = {f"{folder}/install.sh": b"#!/bin/sh\n"}
        if include:
            files[f"{folder}/Labyrinth"] = binary
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_swap_windows_style_moves_the_old_copy_aside(tmp_path):
    target = program(tmp_path)
    new = new_path(target)
    new.write_bytes(b"new")
    swap(target, new, windows=True)
    assert target.read_bytes() == b"new" and not new.exists()
    assert (tmp_path / "Labyrinth.exe.old").read_bytes() == b"old"


def test_swap_uses_the_next_old_name_when_one_is_stuck(tmp_path, monkeypatch):
    target = program(tmp_path)
    stuck = tmp_path / "Labyrinth.exe.old"
    stuck.write_bytes(b"still running")
    real_remove = install._remove
    monkeypatch.setattr(install, "_remove", lambda p: False if p == stuck else real_remove(p))
    new = new_path(target)
    new.write_bytes(b"new")
    swap(target, new, windows=True)
    assert target.read_bytes() == b"new"
    assert (tmp_path / "Labyrinth.exe.1.old").read_bytes() == b"old"


def test_swap_posix_style_replaces_in_place(tmp_path):
    target = program(tmp_path, "labyrinth")
    new = new_path(target)
    new.write_bytes(b"new")
    swap(target, new, windows=False)
    assert target.read_bytes() == b"new" and not list(tmp_path.glob("*.old"))
    if os.name == "posix":
        assert os.access(target, os.X_OK)


def test_failed_swap_restores_the_original(tmp_path, monkeypatch):
    target = program(tmp_path)
    new = new_path(target)
    new.write_bytes(b"new")
    real_replace = os.replace
    calls = []

    def flaky(src, dst):
        calls.append(src)
        if len(calls) == 2:
            raise PermissionError("locked")
        real_replace(src, dst)

    monkeypatch.setattr(install.os, "replace", flaky)
    with pytest.raises(PermissionError):
        swap(target, new, windows=True)
    monkeypatch.undo()
    assert target.read_bytes() == b"old"


def test_cleanup_old(tmp_path):
    target = program(tmp_path)
    (tmp_path / "Labyrinth.exe.old").write_bytes(b"1")
    (tmp_path / "Labyrinth.exe.3.old").write_bytes(b"2")
    assert cleanup_old(target) == []
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Labyrinth.exe"]


def test_can_write(tmp_path):
    assert can_write(tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert not can_write(tmp_path / "missing")


def test_can_write_returns_false_promptly_when_access_is_denied(tmp_path, monkeypatch):
    calls = []

    def denied(path, flags):
        calls.append(path)
        raise PermissionError("denied")

    monkeypatch.setattr(install.os, "open", denied)
    assert not can_write(tmp_path)
    assert 0 < len(calls) <= 5


def test_can_write_retries_past_a_name_collision(tmp_path, monkeypatch):
    real_open = os.open
    calls = []

    def collide_once(path, flags):
        calls.append(path)
        if len(calls) == 1:
            raise FileExistsError("taken")
        return real_open(path, flags)

    monkeypatch.setattr(install.os, "open", collide_once)
    assert can_write(tmp_path)
    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == []


def test_extract_linux_binary(tmp_path):
    archive = tmp_path / "a.tar.gz"
    archive.write_bytes(tarball())
    extract_linux_binary(archive, tmp_path / "out")
    assert (tmp_path / "out").read_bytes() == b"new linux"
    archive.write_bytes(tarball(include=False))
    with pytest.raises(UpdateError, match="did not contain"):
        extract_linux_binary(archive, tmp_path / "out2")
    archive.write_bytes(b"not a tarball")
    with pytest.raises(UpdateError, match="unpacked"):
        extract_linux_binary(archive, tmp_path / "out3")


def test_install_game_windows(serve, tmp_path):
    body = b"new exe"
    server = serve({"/Labyrinth.exe": body})
    target = program(tmp_path)
    install_game(Release("1.2.0", server.url("/Labyrinth.exe"), sha(body)), target,
                 windows=True)
    assert target.read_bytes() == body


def test_install_game_linux(serve, tmp_path):
    data = tarball()
    server = serve({"/l.tar.gz": data})
    target = program(tmp_path, "labyrinth")
    install_game(Release("1.2.0", server.url("/l.tar.gz"), sha(data)), target, windows=False)
    assert target.read_bytes() == b"new linux"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["labyrinth"]


def test_install_game_bad_checksum_leaves_the_program(serve, tmp_path):
    server = serve({"/Labyrinth.exe": b"evil"})
    target = program(tmp_path)
    with pytest.raises(UpdateError, match="checksum"):
        install_game(Release("1.2.0", server.url("/Labyrinth.exe"), "0" * 64), target,
                     windows=True)
    assert target.read_bytes() == b"old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["Labyrinth.exe"]


def test_install_game_needs_a_writable_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(install, "can_write", lambda folder: False)
    with pytest.raises(UpdateError, match="can't write"):
        install_game(Release("1.2.0", "http://x", "0" * 64), program(tmp_path))


def test_screensaver_in_a_writable_folder_swaps_directly(serve, tmp_path):
    body = b"new scr"
    server = serve({"/Labyrinth.scr": body})
    target = program(tmp_path, "Labyrinth.scr")
    staging = tmp_path / "staging"

    def no_elevation(program_path, args):
        raise AssertionError("should not elevate")

    install_screensaver(Release("2.0.0", server.url("/Labyrinth.scr"), sha(body)), target,
                        staging, elevate=no_elevation)
    assert target.read_bytes() == body
    assert list(staging.iterdir()) == []


def test_screensaver_in_a_protected_folder_elevates_the_installed_program(serve, tmp_path,
                                                                          monkeypatch):
    body = b"new scr"
    server = serve({"/Labyrinth.scr": body})
    target = program(tmp_path, "Labyrinth.scr")
    staging = tmp_path / "staging"
    monkeypatch.setattr(install, "can_write", lambda folder: False)
    calls = []

    def elevate(program_path, args):
        calls.append((program_path, list(args)))
        return apply_update(Path(args[1]), Path(args[2]), args[3])

    install_screensaver(Release("2.0.0", server.url("/Labyrinth.scr"), sha(body)), target,
                        staging, elevate=elevate)
    program_path, args = calls[0]
    assert program_path == target
    assert args == [APPLY_FLAG, str(staging / STAGED_NAME), str(target), sha(body)]
    assert target.read_bytes() == body
    assert not (staging / STAGED_NAME).exists()


def test_screensaver_elevation_declined(serve, tmp_path, monkeypatch):
    body = b"new scr"
    server = serve({"/Labyrinth.scr": body})
    target = program(tmp_path, "Labyrinth.scr")
    monkeypatch.setattr(install, "can_write", lambda folder: False)

    def declined(program_path, args):
        raise UpdateError("Update needs administrator permission.")

    with pytest.raises(UpdateError, match="administrator"):
        install_screensaver(Release("2.0.0", server.url("/Labyrinth.scr"), sha(body)), target,
                            tmp_path / "staging", elevate=declined)
    assert target.read_bytes() == b"old"


def test_screensaver_elevated_step_failing(serve, tmp_path, monkeypatch):
    body = b"new scr"
    server = serve({"/Labyrinth.scr": body})
    target = program(tmp_path, "Labyrinth.scr")
    monkeypatch.setattr(install, "can_write", lambda folder: False)
    with pytest.raises(UpdateError, match="could not be installed"):
        install_screensaver(Release("2.0.0", server.url("/Labyrinth.scr"), sha(body)), target,
                            tmp_path / "staging", elevate=lambda p, a: 1)


def test_apply_update_rejects_a_changed_file(tmp_path):
    staged = program(tmp_path, "staged.exe", b"tampered")
    target = program(tmp_path, "Labyrinth.scr")
    assert apply_update(staged, target, sha(b"expected")) == 2
    assert target.read_bytes() == b"old"
    assert not (tmp_path / "Labyrinth.scr.new").exists()


def test_staged_download_is_not_an_executable_name():
    assert STAGED_NAME == "Labyrinth.scr.download"


def test_apply_update_only_replaces_screensavers(tmp_path):
    staged = program(tmp_path, "staged.exe", b"new")
    target = program(tmp_path, "notepad.exe")
    assert apply_update(staged, target, sha(b"new")) == 3
    assert target.read_bytes() == b"old"


def test_relaunch_starts_an_independent_process_without_nuitka_variables(tmp_path,
                                                                         monkeypatch):
    monkeypatch.setenv("NUITKA_ONEFILE_PARENT", "123")
    out = tmp_path / "out.txt"
    code = ("import os, sys; open(sys.argv[1], 'w').write("
            "os.environ.get('NUITKA_ONEFILE_PARENT', 'unset'))")
    relaunch(Path(sys.executable), ["-c", code, str(out)])
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline and not (out.exists() and out.read_text()):
        time.sleep(0.1)
    assert out.read_text() == "unset"


def test_screensaver_main_runs_the_apply_step(tmp_path):
    from maze_saver.__main__ import main
    staged = program(tmp_path, "staged.exe", b"new")
    target = program(tmp_path, "Labyrinth.scr")
    with pytest.raises(SystemExit) as exit_info:
        main([APPLY_FLAG, str(staged), str(target), sha(b"new")])
    assert exit_info.value.code == 0
    assert target.read_bytes() == b"new"


def test_apply_update_hashes_the_copy_in_the_target_folder(tmp_path, monkeypatch):
    staged = program(tmp_path, "staged.exe", b"new")
    target = program(tmp_path, "Labyrinth.scr")
    hashed = []
    real = install.file_sha256

    def spy(path):
        hashed.append(Path(path))
        return real(path)

    monkeypatch.setattr(install, "file_sha256", spy)
    assert apply_update(staged, target, sha(b"new")) == 0
    assert hashed == [new_path(target)]
    assert target.read_bytes() == b"new" and not new_path(target).exists()
