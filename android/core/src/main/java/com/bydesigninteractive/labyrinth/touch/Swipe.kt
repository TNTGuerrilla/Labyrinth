// Turns finger movement on the maze into steering directions. A direction fires as soon as
// the finger has moved far enough with one axis clearly leading, without waiting for it to
// lift; the finger can then turn and fire another direction in the same touch. Coordinates
// are the maze view's pixels (y down), which never rotate, so no turning is needed.
package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/** How far a finger moves before a swipe fires, in dp. */
const val SWIPE_DP = 24f
/** The leading axis must be this many times the other. */
const val SWIPE_DOMINANCE = 1.5f

class SwipeTracker(private val thresholdPx: Float) {
    private var anchorX = 0f
    private var anchorY = 0f
    private var last: Int? = null
    private var active = false

    fun down(x: Float, y: Float) {
        anchorX = x
        anchorY = y
        last = null
        active = true
    }

    /** The direction this movement fires, or null. */
    fun move(x: Float, y: Float): Int? {
        if (!active) return null
        val dx = x - anchorX
        val dy = y - anchorY
        val ax = abs(dx)
        val ay = abs(dy)
        if (max(ax, ay) < thresholdPx || max(ax, ay) < SWIPE_DOMINANCE * min(ax, ay)) return null
        val d = if (ax > ay) (if (dx > 0) E else W) else (if (dy > 0) S else N)
        anchorX = x
        anchorY = y
        if (d == last) return null
        last = d
        return d
    }

    /** A second finger or a cancelled gesture: nothing more fires until the next down. */
    fun cancel() {
        active = false
    }

    /** The finger lifted: whether this touch fired any direction (if not, it was a tap). */
    fun up(): Boolean {
        active = false
        return last != null
    }
}
