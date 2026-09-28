"""Texts and addresses the Info sections share, and the status line beside Check now."""
from __future__ import annotations

from .updater import (AVAILABLE, CHECK_FAILED, CHECKING, DOWNLOADING, FAILED, READY,
                      UP_TO_DATE, CheckReport, Snapshot)

REPO_TEXT = "github.com/TNTGuerrilla/Labyrinth"
REPO_URL = "https://github.com/TNTGuerrilla/Labyrinth"
LICENSE_TEXT = "Licensed under Apache 2.0"
LICENSE_URL = "https://github.com/TNTGuerrilla/Labyrinth/blob/master/LICENSE"
COPYRIGHT = "© 2026 ByDesign Interactive"
SOURCE_ONLY = "Updates are only available in released builds."


def status_text(snapshot: Snapshot, report: CheckReport) -> str:
    """The line beside Check now: an install under way wins, then a check under way, then
    what is on offer, then the outcome of the last check."""
    if snapshot.status == DOWNLOADING:
        return f"Downloading {int(snapshot.progress * 100)}%"
    if snapshot.status == READY:
        return "Restarting"
    if report.status == CHECKING:
        return "Checking..."
    if snapshot.status == FAILED:
        return snapshot.message
    if snapshot.status == AVAILABLE and snapshot.release is not None:
        return f"Version {snapshot.release.version} is available"
    if report.status == CHECK_FAILED:
        return report.message
    if report.status == UP_TO_DATE:
        return "Up to date"
    return ""
