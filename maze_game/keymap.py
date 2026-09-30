"""Game actions and the keys bound to them.

Keys are pygame key names (the strings pygame.key.name returns), so this module has
no pygame dependency. Each action has one or two key slots; slot counts come from
the defaults.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping, Optional, Sequence

DEFAULTS: dict[str, tuple[str, ...]] = {
    "up": ("w", "up"),
    "left": ("a", "left"),
    "down": ("s", "down"),
    "right": ("d", "right"),
    "hint": ("q",),
    "autosolve": ("e",),
    "flash": ("f",),
    "screensaver": ("m",),
    "new": ("r",),
    "replay": ("t",),
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
    "screensaver": "Start screensaver",
    "new": "New maze",
    "replay": "Replay",
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

# Keys with a fixed job that no action may take. Space skips growth and confirms (the
# win panel's New maze); it does different things on different screens, so it is not
# rebindable.
FIXED_KEYS = frozenset({"space"})

# Keys an action falls back to, in order, when its saved keys are missing or refused
# and another action already has every one of its defaults.
SPARE_KEYS = tuple(k for k in "abcdefghijklmnopqrstuvwxyz0123456789" if k not in FIXED_KEYS)


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
        an action with no key, or if `key` is empty (pygame has no name for it, and a
        saved empty name would not load) or fixed (FIXED_KEYS)."""
        mine = self._keys[action]
        if not 0 <= slot < SLOTS[action] or slot > len(mine):
            raise ValueError(f"bad slot {slot} for {action}")
        if not key or key in FIXED_KEYS:
            return False
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
        """Bindings from untrusted data, checked per action. An action that is missing or
        wrong (wrong slot count, unknown key, a fixed key, or a key another action also uses) gets its
        default keys, less any another action already has; so an action added in a later
        release does not reset the user's other keys. If every default is taken, it gets the
        first free key in SPARE_KEYS instead. Only if none is free is the result the full
        default keymap."""
        if not isinstance(raw, dict):
            return cls()
        wanted: dict[str, list[str]] = {}
        for action in ACTIONS:
            keys = raw.get(action)
            if (isinstance(keys, list) and 1 <= len(keys) <= SLOTS[action]
                    and all(isinstance(k, str) and k for k in keys)
                    and not any(k in FIXED_KEYS for k in keys)
                    and len(set(keys)) == len(keys)
                    and (valid_key is None or all(valid_key(k) for k in keys))):
                wanted[action] = keys
        uses = Counter(k for keys in wanted.values() for k in keys)
        kept = {a: keys for a, keys in wanted.items() if all(uses[k] == 1 for k in keys)}
        taken = {k for keys in kept.values() for k in keys}
        bindings: dict[str, list[str]] = {}
        for action in ACTIONS:
            keys = kept.get(action) or [k for k in DEFAULTS[action] if k not in taken]
            if not keys:
                keys = [k for k in SPARE_KEYS if k not in taken
                        and (valid_key is None or valid_key(k))][:1]
            if not keys:
                return cls()
            bindings[action] = keys
            taken.update(keys)
        return cls(bindings)
