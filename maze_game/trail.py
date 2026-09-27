"""The dot's trail on a perfect maze.

Because the maze is a tree there is exactly one route from the start to the dot.
Edges on that route are bright; edges walked and then backed out of are dim.
"""
from __future__ import annotations

from maze_saver.maze import Cell, edge_key

Edge = tuple[Cell, Cell]


class Trail:
    def __init__(self, start: Cell):
        self.route: list[Cell] = [start]
        self.edges: dict[Edge, bool] = {}

    @property
    def cell(self) -> Cell:
        return self.route[-1]

    def move(self, a: Cell, b: Cell) -> None:
        if a != self.route[-1]:
            raise ValueError(f"move from {a} but the trail is at {self.route[-1]}")
        if len(self.route) >= 2 and self.route[-2] == b:
            self.route.pop()
            self.edges[edge_key(a, b)] = False
        else:
            self.route.append(b)
            self.edges[edge_key(a, b)] = True
