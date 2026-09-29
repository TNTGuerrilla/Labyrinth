package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Grid

fun c(x: Int, y: Int) = Cell(x, y)

fun gridOf(cols: Int, rows: Int, vararg edges: Pair<Cell, Cell>): Grid {
    val g = Grid(cols, rows)
    for ((a, b) in edges) g.carve(a, b)
    return g
}

/**
 * A 3x2 perfect maze:
 *
 *     (0,0)-(1,0)-(2,0)
 *       |     |     |
 *     (0,1) (1,1) (2,1)
 *
 * (1,0) is a fork, (0,0) and (2,0) are bends, the bottom row are dead ends.
 */
fun forkGrid(): Grid = gridOf(
    3, 2,
    c(0, 0) to c(1, 0), c(1, 0) to c(2, 0), c(1, 0) to c(1, 1), c(0, 0) to c(0, 1), c(2, 0) to c(2, 1),
)
