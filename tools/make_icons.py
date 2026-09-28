"""Build the desktop icons from the Labyrinth TV launcher icon, so every product shares one icon.

Writes maze_saver/assets/icon.png (256 px, the window icon and the Linux app icon) and
packaging/labyrinth.ico (16 to 256 px, embedded in Labyrinth.exe and Labyrinth.scr).
Needs Pillow: python tools/make_icons.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "android/app/src/main/res/drawable-xxhdpi/ic_launcher_foreground.png"
PNG_OUT = ROOT / "maze_saver/assets/icon.png"
ICO_OUT = ROOT / "packaging/labyrinth.ico"

# The maze drawing sits in a 170 px square centered at (163, 160) of the 324 px adaptive-icon
# foreground; the rest is the safe-zone margin launchers crop away. Cropping 204 px around it
# leaves the drawing about 83% of the tile, like the TV launcher shows it.
CENTER = (163, 160)
CROP = 204
SIZE = 256
MARGIN = 8           # transparent border around the tile, as Windows icons have
RADIUS = 0.18        # tile corner radius, as a fraction of the tile side
SUPERSAMPLE = 4
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def tile(size: int) -> Image.Image:
    """The icon at one size: the maze on a black rounded tile with a transparent margin."""
    big = size * SUPERSAMPLE
    margin = round(MARGIN * size / SIZE) * SUPERSAMPLE
    side = big - 2 * margin
    x, y = CENTER
    half = CROP // 2
    maze = Image.open(SOURCE).convert("RGBA").crop((x - half, y - half, x + half, y + half))
    maze = maze.resize((side, side), Image.Resampling.LANCZOS)
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, side - 1, side - 1), radius=round(side * RADIUS), fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(maze, (margin, margin), mask)
    return out.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    PNG_OUT.parent.mkdir(parents=True, exist_ok=True)
    ICO_OUT.parent.mkdir(parents=True, exist_ok=True)
    tile(SIZE).save(PNG_OUT, optimize=True)
    images = [tile(s) for s in ICO_SIZES]
    images[-1].save(ICO_OUT, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[:-1])
    print(f"Wrote {PNG_OUT.relative_to(ROOT)} and {ICO_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
