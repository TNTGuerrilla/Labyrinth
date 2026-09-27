"""Smooth movement of the dot between cell centers.

The dot is either resting at a cell center (`to` is None) or travelling from `frm`
to the adjacent cell `to`, `t` of the way there. Its logical cell switches at the
midpoint. A chooser decides where to go each time the dot reaches a center, so the
dot never stops between cells.
"""
from __future__ import annotations

from typing import Callable, Optional

from maze_saver.maze import Cell

Move = tuple[Cell, Cell]
Chooser = Callable[[Cell, Optional[Cell]], Optional[Cell]]
_JUST_BEFORE_HALF = 0.5 - 1e-9


class Mover:
    def __init__(self, cell: Cell):
        self.place(cell)

    def place(self, cell: Cell) -> None:
        """Rest at `cell`'s center with no travel history."""
        self.frm: Cell = cell
        self.to: Optional[Cell] = None
        self.t = 0.0
        self.came_from: Optional[Cell] = None

    @property
    def moving(self) -> bool:
        return self.to is not None

    @property
    def cell(self) -> Cell:
        """The logical cell: the destination once past the midpoint."""
        if self.to is not None and self.t >= 0.5:
            return self.to
        return self.frm

    @property
    def next_center(self) -> Cell:
        """The center the dot rests at or is heading to."""
        return self.to if self.to is not None else self.frm

    def position(self) -> tuple[float, float]:
        """Drawn position in cell units; cell (x, y) has its center at (x + 0.5, y + 0.5)."""
        x, y = self.frm
        if self.to is not None:
            x += (self.to[0] - self.frm[0]) * self.t
            y += (self.to[1] - self.frm[1]) * self.t
        return (x + 0.5, y + 0.5)

    def reverse(self) -> None:
        """Turn around mid-glide. The logical cell does not change."""
        if self.to is None:
            return
        self.frm, self.to = self.to, self.frm
        self.t = 1.0 - self.t
        if self.t == 0.5:
            self.t = _JUST_BEFORE_HALF

    def advance(self, distance: float, choose: Chooser) -> list[Move]:
        """Travel up to `distance` cells, asking `choose` at each center. Returns the
        logical moves (a -> b) made, in order."""
        moves: list[Move] = []
        while True:
            if self.to is None:
                nxt = choose(self.frm, self.came_from)
                if nxt is None:
                    return moves
                self.to, self.t = nxt, 0.0
            if distance <= 0:
                return moves
            before = self.t
            self.t = min(1.0, before + distance)
            distance -= self.t - before
            if before < 0.5 <= self.t:
                moves.append((self.frm, self.to))
            if self.t < 1.0:
                return moves
            self.came_from, self.frm, self.to, self.t = self.frm, self.to, None, 0.0
