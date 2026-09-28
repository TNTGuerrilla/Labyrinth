"""In-app updates for the desktop builds: find a newer GitHub release, verify it, and put it
in place of the running program."""

# The screensaver runs the downloaded new program elevated with this flag to install itself.
# Older versions launch newer ones with it, so its meaning and arguments never change:
# --apply-update <staged file> <target .scr> <sha256>
APPLY_FLAG = "--apply-update"
