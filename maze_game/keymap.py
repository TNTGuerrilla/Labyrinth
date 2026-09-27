"""Game actions and the keys bound to them.

Keys are pygame key names (the strings pygame.key.name returns), so this module has
no pygame dependency. Each action has one or two key slots; slot counts come from
the defaults.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Sequence

DEFAULTS: dict[str, tuple[str, ...]] = {
    "up": ("w", "up"),
    "left": ("a", "left"),
    "down": ("s", "down"),
    "right": ("d", "right"),
    "hint": ("q",),
    "autosolve": ("e",),
    "flash": ("f",),
    "new": ("r",),
    "replay": ("t",),
    "confirm": ("space",),
    "small": ("1",),
    "medium": ("2",),
    "large": ("3",),
    "xl": ("4",),
    "custom": ("5",),
    "colors": ("c",),
    "zoom_in": ("=", "[+]"),
    "zoom_out": ("-", "[-]"),
    "zoom_reset": ("z",),
    "settings": ("escape",),
    "fullscreen": ("f11",),
}
ACTIONS = tuple(DEFAULTS)
SLOTS = {action: len(keys) for action, keys in DEFAULTS.items()}
LABELS = {
    "up": "Move up",
    "left": "Move left",
    "down": "Move down",
    "right": "Move right",
    "hint": "Hint",
    "autosolve": "Auto-solve",
    "flash": "Flash finish",
    "new": "New maze",
    "replay": "Replay",
    "confirm": "Skip growth / confirm",
    "small": "Small maze",
    "medium": "Medium maze",
    "large": "Large maze",
    "xl": "XL maze",
    "custom": "Custom size",
    "colors": "Multi-color",
    "zoom_in": "Zoom in",
    "zoom_out": "Zoom out",
    "zoom_reset": "Reset zoom",
    "settings": "Settings",
    "fullscreen": "Fullscreen",
}


def key_label(name: str) -> str:
    """Human-readable key name: "q" -> "Q", "space" -> "Space", "[+]" -> "Num +"."""
    if len(name) == 1:
        return name.upper()
    if name.startswith("[") and name.endswith("]"):
        return "Num " + name[1:-1]
    return name.title()


class Keymap:
    def __init__(self, bindings: Optional[Mapping[str, Sequence[str]]] = None):
        source = DEFAULTS if bindings is None else bindings
        self._keys: dict[str, list[str]] = {a: list(source[a]) for a in ACTIONS}

    def copy(self) -> "Keymap":
        return Keymap(self._keys)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Keymap) and self._keys == other._keys

    def keys_for(self, action: str) -> tuple[str, ...]:
        return tuple(self._keys[action])

    def owner(self, key: str) -> Optional[tuple[str, int]]:
        for action in ACTIONS:
            keys = self._keys[action]
            if key in keys:
                return (action, keys.index(key))
        return None

    def action_for(self, key: str) -> Optional[str]:
        found = self.owner(key)
        return found[0] if found else None

    def set_key(self, action: str, slot: int, key: str) -> bool:
        """Bind `key` to `action`'s slot. If another slot holds `key`, that slot gets this
        slot's old key (a swap). Returns False and changes nothing if the swap would leave
        an action with no key."""
        mine = self._keys[action]
        if not 0 <= slot < SLOTS[action] or slot > len(mine):
            raise ValueError(f"bad slot {slot} for {action}")
        old = mine[slot] if slot < len(mine) else None
        found = self.owner(key)
        if found == (action, slot):
            return True
        if found is not None:
            other = self._keys[found[0]]
            if old is None:
                if len(other) == 1:
                    return False
                del other[found[1]]
            else:
                other[found[1]] = old
        if slot < len(mine):
            mine[slot] = key
        else:
            mine.append(key)
        return True

    def to_json(self) -> dict[str, list[str]]:
        return {action: list(keys) for action, keys in self._keys.items()}

    @classmethod
    def from_json(cls, raw: Any, valid_key: Optional[Callable[[str], bool]] = None) -> "Keymap":
        """Bindings from untrusted data. Anything wrong (missing action, wrong slot count,
        unknown or duplicate key) gives the full default keymap."""
        if not isinstance(raw, dict):
            return cls()
        seen: set[str] = set()
        bindings: dict[str, list[str]] = {}
        for action in ACTIONS:
            keys = raw.get(action)
            if not isinstance(keys, list) or not 1 <= len(keys) <= SLOTS[action]:
                return cls()
            for key in keys:
                if (not isinstance(key, str) or not key or key in seen
                        or (valid_key is not None and not valid_key(key))):
                    return cls()
                seen.add(key)
            bindings[action] = keys
        return cls(bindings)
