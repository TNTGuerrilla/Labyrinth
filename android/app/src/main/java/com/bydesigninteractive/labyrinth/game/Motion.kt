// Smooth movement of the dot between cell centers, ported from maze_game/motion.py.
//
// The dot is either resting at a cell center (to == null) or travelling from frm to the
// adjacent cell to, t of the way there. Its logical cell switches at the midpoint. A
// chooser decides where to go each time the dot reaches a center.
//
// TV addition: pullBack() sends the dot back to frm without recording a move, for a turn
// pressed just too late (see Round.lateTurn).
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell

typealias Move = Pair<Cell, Cell>
typealias Chooser = (Cell, Cell?) -> Cell?

private const val JUST_BEFORE_HALF = 0.5 - 1e-9

class Mover(cell: Cell) {
    var frm: Cell = cell
        private set
    var to: Cell? = null
        private set
    var t = 0.0
        private set
    var cameFrom: Cell? = null
        private set
    /** Heading back to frm after pullBack(); no move is recorded on the way. */
    var returning = false
        private set

    fun place(cell: Cell) {
        frm = cell
        to = null
        t = 0.0
        cameFrom = null
        returning = false
    }

    val moving: Boolean get() = to != null

    /** The logical cell: the destination once past the midpoint (never while returning). */
    val cell: Cell get() {
        val dest = to
        return if (dest != null && !returning && t >= 0.5) dest else frm
    }

    /** The center the dot rests at or is heading to. */
    val nextCenter: Cell get() = if (returning) frm else to ?: frm

    /** Drawn position in cell units; cell (x, y) has its center at (x + 0.5, y + 0.5). */
    fun position(): Pair<Double, Double> {
        var x = frm.x.toDouble()
        var y = frm.y.toDouble()
        val dest = to
        if (dest != null) {
            x += (dest.x - frm.x) * t
            y += (dest.y - frm.y) * t
        }
        return (x + 0.5) to (y + 0.5)
    }

    /** Turn around mid-glide. The logical cell does not change. */
    fun reverse() {
        val dest = to ?: return
        if (returning) return
        to = frm
        frm = dest
        t = 1.0 - t
        if (t == 0.5) t = JUST_BEFORE_HALF
    }

    /** Glide back to frm and rest there, as if the dot had never left it. */
    fun pullBack() {
        if (to != null) returning = true
    }

    /** Travel up to [distance] cells, asking [choose] at each center. Returns the logical moves made. */
    fun advance(distance: Double, choose: Chooser): List<Move> {
        val moves = ArrayList<Move>()
        var left = distance
        while (true) {
            if (returning) {
                if (left <= 0) return moves
                val used = minOf(t, left)
                t -= used
                left -= used
                if (t > 0) return moves
                to = null
                returning = false
                continue
            }
            if (to == null) {
                to = choose(frm, cameFrom) ?: return moves
                t = 0.0
            }
            if (left <= 0) return moves
            val dest = to!!
            val before = t
            t = minOf(1.0, before + left)
            left -= t - before
            if (before < 0.5 && 0.5 <= t) moves.add(frm to dest)
            if (t < 1.0) return moves
            cameFrom = frm
            frm = dest
            to = null
            t = 0.0
        }
    }
}
