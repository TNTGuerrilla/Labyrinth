"""Putting a downloaded version in place of the running program, and starting it."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Callable, Optional, Sequence

from . import APPLY_FLAG
from .net import Progress, UpdateError, download, file_sha256
from .releases import Release

MAX_OLD = 10
LINUX_BINARY = "Labyrinth"
# The download waits here while the installed screensaver asks for administrator rights.
# It is never run, so it does not carry a program's file name.
STAGED_NAME = "Labyrinth.scr.download"
WINDOWS = sys.platform == "win32"

Elevate = Callable[[Path, Sequence[str]], int]


def new_path(target: Path) -> Path:
    return target.with_name(target.name + ".new")


def old_paths(target: Path) -> list[Path]:
    """Where a replaced program goes: X.old, then X.1.old and so on while earlier ones are
    still held by a copy that has not exited yet."""
    return [target.with_name(target.name + ".old")] + [
        target.with_name(f"{target.name}.{n}.old") for n in range(1, MAX_OLD)]


def _remove(path: Path) -> bool:
    """Delete path. True if it is gone afterwards."""
    try:
        path.unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def cleanup_old(target: Path) -> list[Path]:
    """Delete copies replaced by earlier updates. Returns the ones that could not be
    deleted (still running, or in a folder that needs administrator rights)."""
    return [p for p in old_paths(target) if p.exists() and not _remove(p)]


def can_write(folder: Path) -> bool:
    """Whether this process can create files in folder. Tried for real, since os.access
    does not report Windows folder permissions reliably."""
    try:
        handle, probe = tempfile.mkstemp(prefix=".labyrinth-", dir=folder)
    except OSError:
        return False
    os.close(handle)
    _remove(Path(probe))
    return True


def swap(target: Path, new_file: Path, windows: bool = WINDOWS) -> None:
    """Put new_file (in target's folder) at target. Windows cannot overwrite a running
    program but can rename it, so there the old one is moved aside first. Raises OSError;
    when it does, target is unchanged."""
    if not windows:
        os.chmod(new_file, 0o755)
        os.replace(new_file, target)
        return
    old = next((p for p in old_paths(target) if _remove(p)), None)
    if old is None:
        raise OSError(f"Too many earlier copies of {target.name} are still in use.")
    os.replace(target, old)
    try:
        os.replace(new_file, target)
    except OSError:
        os.replace(old, target)
        raise


def install_file(staged: Path, target: Path, windows: bool = WINDOWS) -> None:
    """Copy a verified file into target's folder, then swap it in."""
    new = new_path(target)
    if staged != new:
        shutil.copyfile(staged, new)
    swap(target, new, windows)


def extract_linux_binary(archive: Path, dest: Path) -> None:
    """Copy the program out of a Linux release tarball (Labyrinth-X.Y.Z-linux-x86_64/Labyrinth)."""
    try:
        with tarfile.open(archive, "r:gz") as tar:
            member = next((m for m in tar.getmembers()
                           if m.isfile() and m.name.count("/") == 1
                           and m.name.rsplit("/", 1)[1] == LINUX_BINARY), None)
            if member is None:
                raise UpdateError("The download did not contain the Labyrinth program.")
            source = tar.extractfile(member)
            with source, open(dest, "wb") as out:
                shutil.copyfileobj(source, out)
    except (OSError, tarfile.TarError) as exc:
        raise UpdateError("The download could not be unpacked.") from exc


def install_game(release: Release, target: Path, on_progress: Optional[Progress] = None,
                 windows: bool = WINDOWS) -> None:
    """Download, verify and swap in a new game build. Raises UpdateError; the running
    program stays in place if anything fails."""
    folder = target.parent
    if not can_write(folder):
        raise UpdateError(f"Labyrinth can't write to {folder}. Move Labyrinth to a folder "
                          "you own, then try again.")
    new = new_path(target)
    try:
        if windows:
            download(release.url, new, release.sha256, on_progress)
        else:
            with tempfile.TemporaryDirectory(dir=folder) as tmp:
                archive = Path(tmp) / "update.tar.gz"
                download(release.url, archive, release.sha256, on_progress)
                extract_linux_binary(archive, new)
        swap(target, new, windows)
    except UpdateError:
        _remove(new)
        raise
    except OSError as exc:
        _remove(new)
        raise UpdateError(f"The update could not be installed: {exc.strerror or exc}") from exc


def staging_dir() -> Path:
    """Where the screensaver keeps a download while it asks for administrator rights."""
    base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return Path(base) / "Labyrinth Screensaver" / "update"


def install_screensaver(release: Release, target: Path, staging: Path,
                        on_progress: Optional[Progress] = None,
                        elevate: Optional[Elevate] = None) -> None:
    """Download and verify a new screensaver, then swap it in: directly when its folder is
    writable, otherwise by running the installed screensaver (target) through the UAC prompt
    with APPLY_FLAG. The download sits in a folder the user can write to, so it is never the
    program that gets administrator rights. Raises UpdateError."""
    staged = staging / STAGED_NAME
    try:
        staging.mkdir(parents=True, exist_ok=True)
        download(release.url, staged, release.sha256, on_progress)
        if can_write(target.parent):
            install_file(staged, target)
            return
        if elevate is None:
            from .elevate import run_elevated as elevate
        code = elevate(target, [APPLY_FLAG, str(staged), str(target), release.sha256])
        if code != 0:
            raise UpdateError("The update could not be installed.")
    except OSError as exc:
        raise UpdateError(f"The update could not be installed: {exc.strerror or exc}") from exc
    finally:
        _remove(staged)


def apply_update(staged: Path, target: Path, sha256: str) -> int:
    """The elevated half of a screensaver update. The staged file sits in a folder the user
    can write to, so it is copied into the protected folder first and that copy is checked
    before it replaces target. Returns a process exit code."""
    if target.suffix.lower() != ".scr":
        return 3
    new = new_path(target)
    try:
        shutil.copyfile(staged, new)
        if file_sha256(new) != sha256.lower():
            _remove(new)
            return 2
        swap(target, new)
    except OSError:
        _remove(new)
        return 1
    from .elevate import schedule_delete_at_reboot
    for leftover in cleanup_old(target):
        schedule_delete_at_reboot(leftover)
    return 0


def relaunch(target: Path, args: Sequence[str] = ()) -> None:
    """Start target as a new, independent process. Nuitka's onefile variables are dropped
    so the new program unpacks itself instead of acting as this one's child."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("NUITKA_")}
    options: dict = {}
    if WINDOWS:
        options["creationflags"] = (subprocess.DETACHED_PROCESS
                                    | subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        options["start_new_session"] = True
    subprocess.Popen([str(target), *args], cwd=str(target.parent), env=env, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, **options)
