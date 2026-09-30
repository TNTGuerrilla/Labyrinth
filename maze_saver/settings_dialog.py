"""The Settings dialog Windows opens with /c. tkinter, loaded only in this mode."""
from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional, Sequence

from labyrinth_update.notes import BLANK, BULLET, HEADING, ITEM, NoteLine
from labyrinth_update.updater import (AVAILABLE, CHECK_FAILED, CHECKING, DOWNLOADING, FAILED,
                                      READY, UP_TO_DATE, CheckReport, Snapshot)

from .config import NUMERIC_RANGES, FpsCap, Settings, from_dict, load, save
from .icon import ICON_PATH

open_browser = webbrowser.open

STOP_WAIT_SECONDS = 3  # how long a stopped download gets to clean up before closing

FIELDS = [
    ("min_cells", "Minimum rows/columns"),
    ("max_cells", "Maximum rows/columns"),
    ("max_leads", "Maximum leads"),
    ("coverage", "Screen coverage (%)"),
    ("gen_speed", "Growth speed per lead (steps per second)"),
    ("solve_speed", "Solve speed (steps per second)"),
    ("lookahead", "Look-ahead distance (cells)"),
    ("hold_seconds", "Show solved maze for (seconds)"),
]
INCREMENTS = {"min_cells": 1, "max_cells": 1, "gen_speed": 5, "solve_speed": 1, "lookahead": 1,
             "hold_seconds": 0.5, "max_leads": 1, "coverage": 5}
FPS_LABELS: dict[FpsCap, str] = {"auto": "Match fastest monitor", 60: "60", 120: "120"}


def parse_fields(texts: dict[str, str], fps_label: str,
                 check_updates: bool = True) -> tuple[Optional[Settings], Optional[str]]:
    """Validate dialog text. Returns (settings, None) or (None, error message)."""
    raw: dict = {}
    for name, label in FIELDS:
        low, high, is_int = NUMERIC_RANGES[name]
        try:
            value = float(texts[name].strip())
        except ValueError:
            return None, f"{label} must be a number."
        if is_int and not value.is_integer():
            return None, f"{label} must be a whole number."
        if not low <= value <= high:
            return None, f"{label} must be between {low} and {high}."
        raw[name] = int(value) if is_int else value
    raw["fps_cap"] = {v: k for k, v in FPS_LABELS.items()}.get(fps_label, "auto")
    raw["check_updates"] = check_updates
    return from_dict(raw), None


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def update_row(snapshot: Snapshot, current: str, report: CheckReport = CheckReport(),
               installing: bool = False) -> tuple[str, bool, bool]:
    """(message, show Update, show Dismiss) for the dialog's update row. `installing` is
    set once the download is done and the new version is being put in place."""
    version = snapshot.release.version if snapshot.release is not None else ""
    if snapshot.status == DOWNLOADING and installing:
        return f"Installing version {version}...", False, False
    if snapshot.status == DOWNLOADING:
        return f"Downloading version {version}: {int(snapshot.progress * 100)}%", False, False
    if snapshot.status == READY:
        return (f"Updated to version {version}. It runs the next time the screensaver starts.",
                False, False)
    if report.status == CHECKING:
        can = snapshot.status in (AVAILABLE, FAILED)
        return "Checking...", can, can
    if snapshot.status == FAILED:
        return snapshot.message, True, True
    if snapshot.status == AVAILABLE:
        return f"Version {version} is available.", True, True
    if report.status == CHECK_FAILED:
        return report.message, False, False
    if report.status == UP_TO_DATE:
        return "Up to date", False, False
    return f"Version {current}", False, False


def note_segments(lines: Sequence[NoteLine]) -> list[tuple[str, str]]:
    """(text, tag) pieces for the notes box. The "item" tag indents wrapped rows under the
    text after the bullet (lmargin2); "heading" is bold."""
    out = []
    for line in lines:
        if line.kind == BLANK:
            out.append(("\n", "text"))
        elif line.kind == HEADING:
            out.append((line.text + "\n", "heading"))
        elif line.kind == ITEM:
            out.append((BULLET + line.text + "\n", "item"))
        else:
            out.append((line.text + "\n", "text"))
    if out:
        text, tag = out[-1]
        out[-1] = (text[:-1] if text.endswith("\n") and text != "\n" else text, tag)
    return out


def run_dialog(owner_hwnd: Optional[int] = None, path: Optional[Path] = None, updater=None) -> None:
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import messagebox, ttk

    from labyrinth_update.info import (COPYRIGHT, LICENSE_TEXT, LICENSE_URL, REPO_TEXT,
                                       REPO_URL, SOURCE_ONLY)
    from labyrinth_update.version import running_version

    current = load(path)
    # The update this window started: its StopSwitch, and whether Cancel or OK is waiting
    # for its install to end.
    update: dict = {"switch": None, "closing": False}
    root = tk.Tk()
    root.title("Labyrinth Screensaver Settings")
    try:
        root.iconphoto(True, tk.PhotoImage(master=root, file=str(ICON_PATH)))
    except tk.TclError:
        pass
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=16)
    frame.grid()

    notes_frame = None

    def show_notes(shown) -> None:
        nonlocal notes_frame
        if notes_frame is not None:
            notes_frame.destroy()
        notes_frame = ttk.LabelFrame(info, text=f"Updated to {shown.version}", padding=8)
        notes_frame.grid(row=7, column=0, columnspan=2, sticky="we", pady=(8, 0))
        box = tk.Text(notes_frame, height=8, width=56, wrap="word", relief="flat",
                      borderwidth=0, background=root.cget("background"))
        bar = ttk.Scrollbar(notes_frame, orient="vertical", command=box.yview)
        box.configure(yscrollcommand=bar.set)
        base = tkfont.nametofont("TkDefaultFont")
        bold = base.copy()
        bold.configure(weight="bold")
        box.tag_configure("heading", font=bold)
        box.tag_configure("item", lmargin1=0, lmargin2=base.measure(BULLET))
        for text, tag in note_segments(shown.lines()):
            box.insert("end", text, tag)
        box.configure(state="disabled")
        box.fonts = (bold,)
        box.grid(row=0, column=0, sticky="nsew")
        bar.grid(row=0, column=1, sticky="ns")

    variables: dict[str, tk.StringVar] = {}
    for row, (name, label) in enumerate(FIELDS):
        low, high, _ = NUMERIC_RANGES[name]
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12),
                                          pady=4)
        var = tk.StringVar(value=_fmt(getattr(current, name)))
        ttk.Spinbox(frame, from_=low, to=high, increment=INCREMENTS[name], textvariable=var,
                    width=10).grid(row=row, column=1, sticky="e", pady=4)
        variables[name] = var

    fps_row = len(FIELDS)
    fps_var = tk.StringVar(value=FPS_LABELS[current.fps_cap])
    ttk.Label(frame, text="Frame rate cap").grid(row=fps_row, column=0, sticky="w", padx=(0, 12), pady=4)
    ttk.Combobox(frame, textvariable=fps_var, values=list(FPS_LABELS.values()), state="readonly",
                 width=22).grid(row=fps_row, column=1, sticky="e", pady=4)

    version = updater.current if updater is not None else (running_version("screensaver") or "")
    info = ttk.LabelFrame(frame, text="Info", padding=10)
    info.grid(row=fps_row + 1, column=0, columnspan=2, sticky="we", pady=(12, 0))
    info.columnconfigure(1, weight=1)
    ttk.Label(info, text=f"Labyrinth Screensaver {version}".rstrip()).grid(
        row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(info, text=COPYRIGHT).grid(row=1, column=0, columnspan=2, sticky="w")
    link_font = tkfont.nametofont("TkDefaultFont").copy()
    link_font.configure(underline=True)
    for row, (label, shown, url) in enumerate((("GitHub", REPO_TEXT, REPO_URL),
                                               ("License", LICENSE_TEXT, LICENSE_URL)), 2):
        ttk.Label(info, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=(4, 0))
        link = ttk.Label(info, text=shown, foreground="#0066cc", cursor="hand2", font=link_font)
        link.grid(row=row, column=1, sticky="w", pady=(4, 0))
        link.bind("<Button-1>", lambda _e, u=url: open_browser(u))
    info.link_font = link_font  # tk fonts vanish when garbage collected
    check_var = tk.BooleanVar(value=current.check_updates)
    ttk.Checkbutton(info, text="Check for updates weekly", variable=check_var).grid(
        row=4, column=0, columnspan=2, sticky="w", pady=(8, 4))

    if updater is None:
        ttk.Label(info, text=SOURCE_ONLY).grid(row=5, column=0, columnspan=2, sticky="w")
    else:
        from labyrinth_update.install import StopSwitch, install_screensaver, staging_dir

        def start_update() -> None:
            switch = StopSwitch()
            update["switch"] = switch
            updater.install(lambda release, progress: install_screensaver(
                release, target, staging_dir(), progress, switch=switch))

        box = ttk.Frame(info)
        box.grid(row=5, column=0, columnspan=2, sticky="we", pady=(4, 0))
        box.columnconfigure(0, weight=1)
        status = ttk.Label(box, text="", wraplength=300)
        status.grid(row=0, column=0, sticky="w")
        target = updater.target
        update_button = ttk.Button(box, text="Update", command=start_update)
        dismiss_button = ttk.Button(box, text="Dismiss", command=updater.dismiss)

        actions = ttk.Frame(info)
        actions.grid(row=6, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Button(actions, text="Check now", command=updater.check_now).grid(
            row=0, column=0, padx=(0, 8))
        ttk.Button(actions, text="What's new",
                  command=lambda: show_notes(updater.running_whats_new())).grid(row=0, column=1)

        def poll() -> None:
            if update["closing"] and updater.snapshot.status != DOWNLOADING:
                root.destroy()  # the install that Cancel or OK waited for has ended
                return
            switch = update["switch"]
            message, can_update, can_dismiss = update_row(
                updater.snapshot, updater.current, updater.check_report,
                installing=switch is not None and switch.committed)
            status.configure(text=message)
            for widget, show, column in ((update_button, can_update, 1),
                                         (dismiss_button, can_dismiss, 2)):
                if show:
                    widget.grid(row=0, column=column, padx=(8, 0))
                else:
                    widget.grid_remove()
            root.after(250, poll)

        updater.check(force=True)
        poll()

    if updater is not None:
        shown = updater.start_whats_new()
        if shown is not None:
            show_notes(shown)
            updater.mark_whats_new_seen()  # opening the dialog is what counts as seen

    def close() -> None:
        """Close, asking first while an update downloads: stopping it is safe until the
        install commits. After that the window stays up and closes when the install ends
        (poll does it). A check gets a few seconds, so a stalled server cannot keep a
        hidden process alive."""
        if update["closing"]:
            return
        if updater is not None and updater.snapshot.status == DOWNLOADING:
            switch = update["switch"]
            if switch is not None and not switch.committed:
                if not messagebox.askyesno("Labyrinth Screensaver",
                                           "An update is downloading. Stop it and close?",
                                           parent=root):
                    return
                if switch.stop():
                    root.withdraw()
                    # A stalled read can take up to the download timeout to notice; the
                    # thread is a daemon, so leaving sooner only leaves a partial download.
                    updater.wait(STOP_WAIT_SECONDS)
                    root.destroy()
                    return
            update["closing"] = True
            return
        root.withdraw()
        if updater is not None:
            updater.wait(5)
        root.destroy()

    def on_ok() -> None:
        settings, error = parse_fields({n: v.get() for n, v in variables.items()},
                                       fps_var.get(), check_var.get())
        if error:
            messagebox.showerror("Labyrinth Screensaver", error, parent=root)
            return
        try:
            save(settings, path)
        except OSError as exc:
            messagebox.showerror("Labyrinth Screensaver", f"Could not save settings: {exc}",
                                 parent=root)
            return
        close()

    def on_reset() -> None:
        defaults = Settings()
        for n, v in variables.items():
            v.set(_fmt(getattr(defaults, n)))
        fps_var.set(FPS_LABELS[defaults.fps_cap])
        check_var.set(defaults.check_updates)

    buttons = ttk.Frame(frame)
    buttons.grid(row=fps_row + 2, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(buttons, text="Reset to defaults", command=on_reset).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(buttons, text="Cancel", command=close).grid(row=0, column=1, padx=(0, 8))
    ttk.Button(buttons, text="OK", command=on_ok).grid(row=0, column=2)
    root.bind("<Return>", lambda _e: on_ok())
    root.bind("<Escape>", lambda _e: close())
    root.protocol("WM_DELETE_WINDOW", close)

    root.update_idletasks()
    if owner_hwnd:
        from . import monitors
        toplevel = monitors.get_parent(root.winfo_id())
        monitors.set_owner(toplevel, owner_hwnd)
    root.mainloop()
