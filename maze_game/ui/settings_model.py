"""Settings panel state: tabs, rows and the draft being edited. No drawing here."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ..config import GameSettings
from ..difficulty import DIFFICULTIES, LABELS as DIFFICULTY_LABELS, MIN_CUSTOM, PRESETS
from ..keymap import LABELS as ACTION_LABELS, SLOTS, Keymap, key_label
from labyrinth_update.info import COPYRIGHT, LICENSE_TEXT, REPO_TEXT, SOURCE_ONLY

TABS = ("Gameplay", "Difficulty", "Controls", "Info")
UNSELECTABLE = ("header", "info")
LINK_TEXT = {"github": REPO_TEXT, "license": LICENSE_TEXT}


@dataclass(frozen=True)
class Row:
    kind: str  # "header", "bool", "choice", "number", "key", "button", "info" or "link"
    label: str
    name: str  # settings field, action (key rows) or button id
    lo: float = 0
    hi: float = 0
    step: float = 1
    choices: tuple = ()  # (value, label) pairs for "choice"
    slot: int = 0  # key slot for "key" rows


@dataclass(frozen=True)
class InfoState:
    """What the Info tab shows; the game refreshes it every frame from its updater."""
    version: str = ""  # "" when unknown
    updates: bool = False  # an updater exists (a released build)
    status: str = ""  # the line beside Check now (labyrinth_update.info.status_text)
    can_update: bool = False  # an update is on offer (available, or failed and retryable)


def header(title: str) -> Row:
    """A section title: drawn above its rows, never selected."""
    return Row("header", title, "")


GAMEPLAY_ROWS = (
    header("Movement"),
    Row("bool", "Follow bends", "follow_bends"),
    Row("number", "Glide speed (cells/s)", "glide_speed", 2, 40, 1),
    Row("number", "Turn pause (s)", "turn_pause", 0, 1, 0.05),
    header("Display"),
    Row("bool", "Multi-color", "multicolor"),
    Row("bool", "Show grid", "show_grid"),
    Row("number", "Grid strength (%)", "grid_strength", 10, 100, 10),
    Row("number", "Screen coverage (%)", "coverage", 50, 100, 5),
    header("Maze growth"),
    Row("choice", "Maze generation", "animated",
        choices=((True, "Animated"), (False, "Instant"))),
    Row("number", "Growth speed (steps/s per lead)", "gen_speed", 5, 1000, 5),
    Row("number", "Max leads", "max_leads", 2, 16, 1),
    header("Assists"),
    Row("number", "Auto-solve speed (steps/s)", "solve_speed", 2, 500, 2),
    Row("number", "Solver look-ahead (cells)", "lookahead", 0, 12, 1),
    Row("number", "Hint length (cells)", "hint_length", 2, 40, 1),
)
CONTROL_GROUPS = (
    ("Movement", ("up", "left", "down", "right")),
    ("Assists", ("hint", "autosolve", "flash")),
    ("Round", ("new", "replay", "confirm")),
    ("Maze size", ("small", "medium", "large", "xl", "custom")),
    ("View", ("colors", "zoom_in", "zoom_out", "zoom_reset", "fullscreen")),
    ("Menu", ("settings",)),
)
FOOTER_ROWS = (Row("button", "Apply", "apply"), Row("button", "Cancel", "cancel"))


def difficulty_label(d: str) -> str:
    if d == "custom":
        return "Custom"
    lo, hi = PRESETS[d]
    return f"{DIFFICULTY_LABELS[d]} ({lo}-{hi})"


class SettingsModel:
    def __init__(self, settings: GameSettings, keymap: Keymap, ceiling: int,
                 resolution: tuple[int, int], info: InfoState = InfoState()):
        self.draft = settings
        self.keys = keymap.copy()
        self.ceiling = ceiling
        self.resolution = tuple(resolution)
        self.tab = 0
        self.index = 0
        self.capturing = False
        self.pending_swap: Optional[str] = None
        self.message = ""
        self.info = info
        self.select(0)

    def rows(self) -> list[Row]:
        return list(self._tab_rows()) + list(FOOTER_ROWS)

    def _tab_rows(self) -> tuple:
        if self.tab == 0:
            return GAMEPLAY_ROWS
        if self.tab == 1:
            return (
                header("Maze size"),
                Row("choice", "Difficulty", "difficulty",
                    choices=tuple((d, difficulty_label(d)) for d in DIFFICULTIES)),
                Row("number", "Custom min", "custom_min", MIN_CUSTOM, self.ceiling, 1),
                Row("number", "Custom max", "custom_max", MIN_CUSTOM, self.ceiling, 1),
                header("Performance"),
                Row("button", "Run benchmark", "benchmark"),
            )
        if self.tab == 2:
            rows = []
            for title, actions in CONTROL_GROUPS:
                rows.append(header(title))
                rows.extend(Row("key", ACTION_LABELS[a] + (" (alt)" if s else ""), a, slot=s)
                            for a in actions for s in range(SLOTS[a]))
            rows.append(Row("button", "Reset to defaults", "reset_keys"))
            return tuple(rows)
        return self._info_rows()

    def _info_rows(self) -> tuple:
        i = self.info
        rows = [Row("info", f"Labyrinth {i.version}".rstrip(), "version"),
                Row("info", COPYRIGHT, "copyright"),
                Row("link", "GitHub", "github"),
                Row("link", "License", "license"),
                header("Updates"),
                Row("bool", "Check for updates weekly", "check_updates")]
        if not i.updates:
            rows.append(Row("info", SOURCE_ONLY, "source_only"))
            return tuple(rows)
        rows.append(Row("button", "Check now", "check_now"))
        if i.can_update:
            rows.append(Row("button", "Update", "update"))
        rows.append(Row("button", "What's new", "whats_new"))
        return tuple(rows)

    def set_info(self, info: InfoState) -> None:
        """New Info content. Rows can appear (Update), so the selection follows its row."""
        if info == self.info:
            return
        selected = self.selected
        self.info = info
        rows = self.rows()
        index = next((i for i, r in enumerate(rows) if r == selected),
                     min(self.index, len(rows) - 1))
        capturing = self.capturing
        self.select(index)
        self.capturing = capturing

    @property
    def selected(self) -> Row:
        return self.rows()[self.index]

    def bench_text(self) -> str:
        d = self.draft
        if d.bench_size is not None and d.bench_resolution == self.resolution:
            return f"Recommended max: {d.bench_size}"
        return "Not run for this screen size"

    def value_text(self, row: Row) -> str:
        if row.kind == "bool":
            return "On" if getattr(self.draft, row.name) else "Off"
        if row.kind == "choice":
            value = getattr(self.draft, row.name)
            return next(label for v, label in row.choices if v == value)
        if row.kind == "number":
            value = getattr(self.draft, row.name)
            return str(int(value)) if float(value).is_integer() else f"{value:g}"
        if row.kind == "key":
            if self.capturing and row == self.selected:
                return "Press a key..."
            keys = self.keys.keys_for(row.name)
            return key_label(keys[row.slot]) if row.slot < len(keys) else "(none)"
        if row.kind == "link":
            return LINK_TEXT[row.name]
        if row.name == "check_now":
            return self.info.status
        if row.name == "benchmark":
            return self.bench_text()
        return ""

    def select(self, index: int, direction: int = 1) -> None:
        """Select a row, stepping past section headers and info lines in `direction`."""
        rows = self.rows()
        index %= len(rows)
        while rows[index].kind in UNSELECTABLE:
            index = (index + direction) % len(rows)
        self.index = index
        self.capturing = False

    def set_tab(self, tab: int) -> None:
        self.tab = tab % len(TABS)
        self.select(0)
        self.pending_swap = None
        self.message = ""

    def change(self, delta: int) -> None:
        row = self.selected
        if row.kind not in ("bool", "choice", "number"):
            return
        value = getattr(self.draft, row.name)
        if row.kind == "bool":
            new = not value
        elif row.kind == "choice":
            values = [v for v, _ in row.choices]
            new = values[(values.index(value) + delta) % len(values)]
        else:
            new = min(row.hi, max(row.lo, value + delta * row.step))
            new = int(new) if isinstance(value, int) else round(float(new), 4)
        self.draft = replace(self.draft, **{row.name: new})

    def activate(self) -> Optional[str]:
        row = self.selected
        if row.kind in ("bool", "choice"):
            self.change(1)
        elif row.kind == "key":
            self.capturing = True
            self.message = ""
        elif row.kind == "button":
            if row.name == "reset_keys":
                self.keys = Keymap()
                return None
            return row.name
        elif row.kind == "link":
            return row.name
        return None

    def capture(self, key_name: str) -> None:
        """The key pressed while a key row is waiting. Esc cancels."""
        self.capturing = False
        if key_name == "escape":
            return
        row = self.selected
        owner = self.keys.owner(key_name)
        if owner is not None and owner != (row.name, row.slot):
            self.pending_swap = key_name
            self.message = (f"{key_label(key_name)} is used by {ACTION_LABELS[owner[0]]}. "
                            "Enter swaps, Esc cancels.")
            return
        self.keys.set_key(row.name, row.slot, key_name)

    def handle(self, nav: str, now: float = 0.0) -> Optional[str]:
        if self.pending_swap is not None:
            if nav == "confirm":
                row = self.selected
                if self.keys.set_key(row.name, row.slot, self.pending_swap):
                    self.message = ""
                else:
                    self.message = "Can't swap: that would leave an action with no key."
                self.pending_swap = None
            elif nav == "cancel":
                self.pending_swap = None
                self.message = ""
            return None
        if nav == "up":
            self.select(self.index - 1, -1)
        elif nav == "down":
            self.select(self.index + 1)
        elif nav == "left":
            self.change(-1)
        elif nav == "right":
            self.change(1)
        elif nav == "tab":
            self.set_tab(self.tab + 1)
        elif nav == "confirm":
            return self.activate()
        elif nav == "cancel":
            return "cancel"
        return None

    def result(self) -> tuple[GameSettings, Keymap]:
        s = self.draft
        if s.custom_min > s.custom_max:
            s = replace(s, custom_min=s.custom_max, custom_max=s.custom_min)
        return s, self.keys
