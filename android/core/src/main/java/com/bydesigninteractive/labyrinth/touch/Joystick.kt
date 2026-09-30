// The touch joystick's rule: four 90-degree wedges around the axes, and a dead zone in the
// middle. Coordinates are relative to the disc's center, y down, as the player sees them.
package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import kotlin.math.abs
import kotlin.math.hypot

/** The dead zone's radius, as a fraction of the disc's. */
const val JOYSTICK_DEAD_ZONE = 0.25f

/** The wedge under a thumb at ([dx], [dy]) from the center, or null in the dead zone. */
fun wedge(dx: Float, dy: Float, radius: Float): Int? {
    if (hypot(dx, dy) < radius * JOYSTICK_DEAD_ZONE) return null
    return if (abs(dx) > abs(dy)) (if (dx > 0) E else W) else (if (dy > 0) S else N)
}
