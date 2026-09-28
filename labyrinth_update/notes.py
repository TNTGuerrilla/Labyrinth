"""Release notes: the part of a GitHub release body the programs show, and how it is laid
out as plain text. The body's `---` line and everything after it (the SHA-256 line and the
install steps) stay on GitHub only."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

CUTOFF = "---"
RELEASES_TEXT = "github.com/TNTGuerrilla/Labyrinth/releases"
MORE_TEXT = f"More at {RELEASES_TEXT}"
BULLET = "- "  # drawn before an item; its wrapped rows line up after it
HEADING, TEXT, ITEM, BLANK = "heading", "text", "item", "blank"

Measure = Callable[[str], int]  # pixel width of a string in the font it is drawn with


@dataclass(frozen=True)
class NoteLine:
    kind: str  # HEADING, TEXT, ITEM (a bullet) or BLANK
    text: str = ""
    cont: bool = False  # a wrapped continuation of the row above


def extract_notes(body: object) -> str:
    """The shown part of a release body: everything before the first line that is `---`,
    without leading or trailing blank lines. "" for a missing or empty body."""
    if not isinstance(body, str):
        return ""
    kept: list[str] = []
    for line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.strip() == CUTOFF:
            break
        kept.append(line.rstrip())
    while kept and not kept[0].strip():
        kept.pop(0)
    while kept and not kept[-1]:
        kept.pop()
    return "\n".join(kept)


def _clean(text: str) -> str:
    return text.replace("**", "").replace("`", "").strip()


def parse_notes(text: str) -> list[NoteLine]:
    """Headings (# marks removed), bullets (- or *), plain lines, and single blank lines
    between them. Bold and code marks are dropped; nothing else of Markdown is rendered."""
    lines: list[NoteLine] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if line.startswith("#"):
            kind, body = HEADING, line.lstrip("#")
        elif line.startswith(("- ", "* ")):
            kind, body = ITEM, line[2:]
        else:
            kind, body = TEXT, line
        body = _clean(body)
        if not body:
            if lines and lines[-1].kind != BLANK:
                lines.append(NoteLine(BLANK))
            continue
        lines.append(NoteLine(kind, body))
    while lines and lines[-1].kind == BLANK:
        lines.pop()
    return lines


def _split_word(word: str, width: int, measure: Measure) -> list[str]:
    """A word wider than the line, cut into pieces that fit (at least one character each)."""
    pieces: list[str] = []
    piece = ""
    for ch in word:
        if piece and measure(piece + ch) > width:
            pieces.append(piece)
            piece = ch
        else:
            piece += ch
    if piece:
        pieces.append(piece)
    return pieces


def _wrap_text(text: str, width: int, measure: Measure) -> list[str]:
    rows: list[str] = []
    row = ""
    for word in text.split():
        candidate = f"{row} {word}" if row else word
        if measure(candidate) <= width:
            row = candidate
            continue
        if row:
            rows.append(row)
        pieces = _split_word(word, width, measure) if measure(word) > width else [word]
        rows.extend(pieces[:-1])
        row = pieces[-1]
    if row:
        rows.append(row)
    return rows


def wrap_notes(lines: Sequence[NoteLine], width: int, measure: Measure) -> list[NoteLine]:
    """Lines broken at spaces to fit `width` pixels as `measure` counts them. An item's text
    wraps in the room after its bullet; every row after a line's first has cont=True."""
    out: list[NoteLine] = []
    indent = measure(BULLET)
    for line in lines:
        if line.kind == BLANK:
            out.append(line)
            continue
        room = max(1, width - indent) if line.kind == ITEM else width
        for i, row in enumerate(_wrap_text(line.text, room, measure)):
            out.append(NoteLine(line.kind, row, cont=i > 0))
    return out


def fit_lines(lines: Sequence[NoteLine], max_lines: int,
              more: Sequence[NoteLine]) -> list[NoteLine]:
    """The rows that fit in `max_lines`. When some are left out, the last rows are `more`
    (the wrapped "More at ..." line) instead, and a blank row never sits just above it."""
    if len(lines) <= max_lines:
        return list(lines)
    keep = max(0, max_lines - len(more))
    kept = list(lines[:keep])
    while kept and kept[-1].kind == BLANK:
        kept.pop()
    return kept + list(more)[:max(0, max_lines - len(kept))]
