"""The Settings dialog Windows opens with /c. tkinter, loaded only in this mode."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from .config import NUMERIC_RANGES, FpsCap, Settings, from_dict, load, save
from .icon import ICON_PATH

FIELDS = [
    ("min_cells", "Minimum rows/columns"),
    ("max_cells", "Maximum rows/columns"),
    ("max_leads", "Maximum leads"),
    ("gen_speed", "Growth speed per lead (steps per second)"),
    ("solve_speed", "Solve speed (steps per second)"),
    ("lookahead", "Look-ahead distance (cells)"),
    ("hold_seconds", "Show solved maze for (seconds)"),
]
INCREMENTS = {"min_cells": 1, "max_cells": 1, "gen_speed": 5, "solve_speed": 1, "lookahead": 1,
             "hold_seconds": 0.5, "max_leads": 1}
FPS_LABELS: dict[FpsCap, str] = {"auto": "Match fastest monitor", 60: "60", 120: "120"}


def parse_fields(texts: dict[str, str], fps_label: str) -> tuple[Optional[Settings], Optional[str]]:
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
    return from_dict(raw), None


def _fmt(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def run_dialog(owner_hwnd: Optional[int] = None, path: Optional[Path] = None) -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    current = load(path)
    root = tk.Tk()
    root.title("Labyrinth Screensaver Settings")
    try:
        root.iconphoto(True, tk.PhotoImage(master=root, file=str(ICON_PATH)))
    except tk.TclError:
        pass
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=16)
    frame.grid()

    variables: dict[str, tk.StringVar] = {}
    for row, (name, label) in enumerate(FIELDS):
        low, high, _ = NUMERIC_RANGES[name]
        ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=4)
        var = tk.StringVar(value=_fmt(getattr(current, name)))
        ttk.Spinbox(frame, from_=low, to=high, increment=INCREMENTS[name], textvariable=var,
                    width=10).grid(row=row, column=1, sticky="e", pady=4)
        variables[name] = var

    fps_row = len(FIELDS)
    fps_var = tk.StringVar(value=FPS_LABELS[current.fps_cap])
    ttk.Label(frame, text="Frame rate cap").grid(row=fps_row, column=0, sticky="w", padx=(0, 12), pady=4)
    ttk.Combobox(frame, textvariable=fps_var, values=list(FPS_LABELS.values()), state="readonly",
                 width=22).grid(row=fps_row, column=1, sticky="e", pady=4)

    def on_ok() -> None:
        settings, error = parse_fields({n: v.get() for n, v in variables.items()}, fps_var.get())
        if error:
            messagebox.showerror("Labyrinth Screensaver", error, parent=root)
            return
        try:
            save(settings, path)
        except OSError as exc:
            messagebox.showerror("Labyrinth Screensaver", f"Could not save settings: {exc}", parent=root)
            return
        root.destroy()

    def on_reset() -> None:
        defaults = Settings()
        for n, v in variables.items():
            v.set(_fmt(getattr(defaults, n)))
        fps_var.set(FPS_LABELS[defaults.fps_cap])

    buttons = ttk.Frame(frame)
    buttons.grid(row=fps_row + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
    ttk.Button(buttons, text="Reset to defaults", command=on_reset).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(buttons, text="Cancel", command=root.destroy).grid(row=0, column=1, padx=(0, 8))
    ttk.Button(buttons, text="OK", command=on_ok).grid(row=0, column=2)
    root.bind("<Return>", lambda _e: on_ok())
    root.bind("<Escape>", lambda _e: root.destroy())

    root.update_idletasks()
    if owner_hwnd:
        from . import monitors
        toplevel = monitors.get_parent(root.winfo_id())
        monitors.set_owner(toplevel, owner_hwnd)
    root.mainloop()
