// Drag steering: the finger draws the dot's path. Every cell the finger crosses joins the
// traced path if the dot could step into it from the path's last cell (next door, no wall
// between); cells across a wall are ignored. Going back onto the previous cell erases the
// last one. The game never chooses a branch: the player traces every turn.
package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Grid
import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.sign

/**
 * The cells a straight finger movement crosses, from (x0, y0) to (x1, y1) in cell units,
 * in order and without gaps (side to side, never corner to corner).
 */
fun cellsAlong(x0: Double, y0: Double, x1: Double, y1: Double): List<Cell> {
    val cx0 = floor(x0).toInt()
    val cy0 = floor(y0).toInt()
    val out = arrayListOf(Cell(cx0, cy0))
    if (!x0.isFinite() || !y0.isFinite() || !x1.isFinite() || !y1.isFinite()) {
        return out
    }
    val ex = floor(x1).toInt()
    val ey = floor(y1).toInt()
    var cx = cx0
    var cy = cy0
    val dx = x1 - x0
    val dy = y1 - y0
    val stepX = sign(dx).toInt()
    val stepY = sign(dy).toInt()
    var nx = abs(ex - cx)
    var ny = abs(ey - cy)
    val tDeltaX = if (dx != 0.0) 1.0 / abs(dx) else Double.MAX_VALUE
    val tDeltaY = if (dy != 0.0) 1.0 / abs(dy) else Double.MAX_VALUE
    var tMaxX = if (dx != 0.0) (if (stepX > 0) cx + 1 - x0 else x0 - cx) / abs(dx) else Double.MAX_VALUE
    var tMaxY = if (dy != 0.0) (if (stepY > 0) cy + 1 - y0 else y0 - cy) / abs(dy) else Double.MAX_VALUE
    while (nx > 0 || ny > 0) {
        if (ny == 0 || (nx > 0 && tMaxX <= tMaxY)) {
            cx += stepX
            tMaxX += tDeltaX
            nx--
        } else {
            cy += stepY
            tMaxY += tDeltaY
            ny--
        }
        out.add(Cell(cx, cy))
    }
    return out
}

class Trace {
    private val path = ArrayList<Cell>()

    /** The traced cells the dot has not reached yet, in order. */
    val cells: List<Cell> get() = path

    fun clear() = path.clear()

    /**
     * The finger entered [cell]. [from] is where the trace continues from while it is empty:
     * the cell the dot is at or heading to. Returns whether the trace changed.
     */
    fun enter(grid: Grid, cell: Cell, from: Cell): Boolean {
        val last = path.lastOrNull() ?: from
        if (cell == last) return false
        val previous = when (path.size) {
            0 -> null
            1 -> from
            else -> path[path.size - 2]
        }
        if (cell == previous) {
            path.removeAt(path.size - 1)
            return true
        }
        if (cell !in grid.openNeighbors(last)) return false
        path.add(cell)
        return true
    }

    /** The dot arrived at [cell]: it leaves the trace when it is the next one. */
    fun reached(cell: Cell) {
        if (path.firstOrNull() == cell) path.removeAt(0)
    }
}
