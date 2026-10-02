// Choosers: what decides where the dot goes each time it reaches a cell center. Ported
// from maze_game/steering.py (keyboard and auto-solve only; the TV has no mouse).
//
// TV addition: with bend assist off, pauseAtForks makes the dot pause at forks the way
// bend assist does, so a slow remote still gets time to turn.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Grid
import com.bydesigninteractive.labyrinth.maze.direction

/**
 * Keyboard (remote) steering.
 *
 * Bend assist off: the most recently pressed held direction steers; the dot stops where
 * that way is closed. With pauseAtForks, it also pauses at forks for `pause` seconds
 * unless a direction was pressed since it left the previous cell.
 *
 * Bend assist on: held keys keep the dot moving along its heading and through corridor
 * bends; only a fresh press (the request) turns it into a side passage; forks pause for
 * `pause` seconds so the player can react, then carry straight on if a key is still held.
 * Branches that visibly dead-end within the look-ahead distance are not counted as choices.
 */
class KeyboardSteer {
    val held = ArrayList<Int>()

    /**
     * A swipe, or a button arrow with Steering on Run straight: nothing is held, but the dot runs on
     * (through bends with bend assist on, straight with it off).
     */
    var coast = false
    var request: Int? = null
    var now = 0.0
        private set
    private var pauseCell: Cell? = null
    private var pauseUntil = 0.0
    private var stopped = false
    private var lastCell: Cell? = null

    fun press(d: Int) {
        held.remove(d)
        held.add(d)
        request = d
    }

    fun release(d: Int) {
        held.remove(d)
    }

    fun clear() {
        held.clear()
        request = null
        pauseCell = null
        stopped = false
        lastCell = null
    }

    /** A new round, or a replay: a buffered request is stale. Held keys are kept. */
    fun resetRound() {
        request = null
        forgetPosition()
    }

    /** Something else moved the dot (auto-solve): pause, stop and last-cell tracking are stale. */
    fun forgetPosition() {
        pauseCell = null
        stopped = false
        lastCell = null
    }

    fun tick(dt: Double) {
        now += dt
    }

    val wanted: Int? get() = held.lastOrNull()

    fun choose(
        grid: Grid, cell: Cell, cameFrom: Cell?, followBends: Boolean, stops: Collection<Cell>, end: Cell,
        lookahead: Int, pause: Double, pauseAtForks: Boolean = false,
    ): Cell? {
        if (lastCell != cell) {
            pauseCell = null
            stopped = false
        }
        lastCell = cell
        if (!followBends) {
            return if (coast) straight(grid, cell, cameFrom, stops)
            else classic(grid, cell, cameFrom, stops, pause, pauseAtForks)
        }
        val result = guided(grid, cell, cameFrom, stops, end, lookahead, pause)
        if (result != null) stopped = false
        return result
    }

    private fun classic(
        grid: Grid, cell: Cell, cameFrom: Cell?, stops: Collection<Cell>, pause: Double, pauseAtForks: Boolean,
    ): Cell? {
        val d = wanted ?: return null
        if ((grid.openDirs(cell) and d) == 0) return null
        // Forks are counted from every opening except the way it came, without look-ahead, so a
        // short dead end ahead does not hide a live branch (as with a straight swipe).
        if (pauseAtForks && pause > 0 && request == null && cameFrom != null && cell !in stops &&
            grid.openNeighbors(cell).filter { it != cameFrom }.size >= 2
        ) {
            if (pauseCell != cell) {
                pauseCell = cell
                pauseUntil = now + pause
                return null
            }
            if (now < pauseUntil) return null
        }
        // Leaving: a press from before this point is used up, so the next fork only skips
        // its pause for a press made on the way there.
        request = null
        pauseCell = null
        return cell.step(d)
    }

    /**
     * A swipe with bend assist off: the dot runs straight and stops at the first bend, wall or
     * fork. A swipe (the request) turns it at the first cell where that way is open; at a stop
     * where it is not open, it is dropped. Forks are counted from every opening except the way it
     * came, without look-ahead, so a short dead end ahead does not hide a live branch.
     */
    private fun straight(grid: Grid, cell: Cell, cameFrom: Cell?, stops: Collection<Cell>): Cell? {
        val r = request
        if (r != null && (grid.openDirs(cell) and r) != 0) {
            request = null
            return cell.step(r)
        }
        if (cameFrom == null || cell in stops) {
            request = null
            return null
        }
        val heading = direction(cameFrom, cell)
        if ((grid.openDirs(cell) and heading) == 0 ||
            grid.openNeighbors(cell).filter { it != cameFrom }.size >= 2
        ) {
            request = null
            return null
        }
        return cell.step(heading)
    }

    private fun exits(grid: Grid, cell: Cell, cameFrom: Cell, end: Cell, lookahead: Int): List<Cell> {
        val raw = grid.openNeighbors(cell).filter { it != cameFrom }
        // Pruning only classifies forks; it must never remove the only way forward.
        return raw.filter { !deadEndWithin(grid, cell, it, end, lookahead) }.ifEmpty { raw }
    }

    private fun guided(
        grid: Grid, cell: Cell, cameFrom: Cell?, stops: Collection<Cell>, end: Cell, lookahead: Int, pause: Double,
    ): Cell? {
        val r = request
        if (r != null) {
            if ((grid.openDirs(cell) and r) != 0) {
                request = null
                pauseCell = null
                return cell.step(r)
            }
            if (stopped) {
                // Standing still: an unusable press does nothing rather than launching the
                // dot along its old, stale heading.
                request = null
                return null
            }
        }
        if (cameFrom == null || cell in stops) {
            request = null
            stopped = true
            return null
        }
        val heading = direction(cameFrom, cell)
        val exits = exits(grid, cell, cameFrom, end, lookahead)
        if (exits.isEmpty()) {
            request = null
            stopped = true
            return null
        }
        if (exits.size == 1) {
            if (stopped) {
                request = null
                return null
            }
            if (held.isEmpty() && !coast) {
                request = null
                stopped = true
                return null
            }
            val next = exits[0]
            if (direction(cell, next) != heading) request = null
            return next
        }
        if (pause > 0) {
            if (pauseCell != cell) {
                pauseCell = cell
                pauseUntil = now + pause
                return null
            }
            if (now < pauseUntil) return null
        }
        request = null
        if (stopped) return null
        val ahead = cell.step(heading)
        if (held.isNotEmpty() && ahead in exits) {
            pauseCell = null
            return ahead
        }
        stopped = true
        return null
    }
}

/** True if pressing direction d means turning around on the segment frm -> to. */
fun isReverse(frm: Cell, to: Cell?, d: Int): Boolean = to != null && direction(to, frm) == d

/** Drives the dot along the shortest route from wherever it is to the end. */
class AutoSteer(private val towardEnd: Map<Cell, Cell>, private val end: Cell) {
    var done = false
        private set

    fun choose(cell: Cell, cameFrom: Cell? = null): Cell? {
        if (done) return null
        if (cell == end) {
            done = true
            return null
        }
        return towardEnd[cell]
    }
}
