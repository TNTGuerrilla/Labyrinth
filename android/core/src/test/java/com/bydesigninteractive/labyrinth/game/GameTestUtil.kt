package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Grid
import kotlin.math.abs
import kotlin.random.Random

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

/** Follows a fixed list of cells. */
class PathSteer(cells: Iterable<Cell>) {
    private val cells = ArrayDeque(cells.toList())

    val done: Boolean get() = cells.isEmpty()

    fun choose(cell: Cell, cameFrom: Cell? = null): Cell? {
        val next = cells.firstOrNull() ?: return null
        if (abs(next.x - cell.x) + abs(next.y - cell.y) != 1) {
            cells.clear()
            return null
        }
        cells.removeFirst()
        return next
    }
}

val FAST = GameSettings(genSpeed = 1000.0)

/** A round whose maze has finished growing. */
fun grown(cols: Int = 6, rows: Int = 4, settings: GameSettings = FAST, seed: Int = 1): Round {
    val r = Round.create(cols, rows, settings, Random(seed))
    repeat(100000) {
        if (r.phase == RoundPhase.PLAY) return r
        r.update(1.0 / 60)
    }
    throw AssertionError("growth never finished")
}

/**
 * A 4x2 maze with a fork at (1,1) and a dead-end side branch north of it:
 *
 *           (1,0)
 *             |
 *     (0,1)-(1,1)-(2,1)-(3,1)
 *
 * The other top-row cells are not connected and never visited.
 */
fun lineWithBranch(): Grid = gridOf(4, 2, c(0, 1) to c(1, 1), c(1, 1) to c(2, 1), c(2, 1) to c(3, 1), c(1, 1) to c(1, 0))
