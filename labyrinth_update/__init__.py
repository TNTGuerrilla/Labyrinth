"""In-app updates for the desktop builds: find a newer GitHub release, verify it, and put it
in place of the running program."""

# The installed screensaver runs itself elevated with this flag to install a downloaded
# version. Older versions may launch newer ones with it, so its meaning and arguments never change:
# --apply-update <staged file> <target .scr> <sha256>
APPLY_FLAG = "--apply-update"
