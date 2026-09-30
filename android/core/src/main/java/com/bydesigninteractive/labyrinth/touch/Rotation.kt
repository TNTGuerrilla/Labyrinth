// Which way is up for the player, and what that means for the maze. The phone game's window
// never rotates: the maze stays fixed to the glass. "turns" is the direction the player's up
// points on the physical screen, in clockwise quarter turns from the natural up: 0 natural,
// 1 the device's right edge up, 2 upside down, 3 its left edge up.
package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.maze.DIRECTIONS
import kotlin.math.abs

/** How the player may hold the phone: the Orientation setting. */
enum class Hold { AUTO, PORTRAIT, LANDSCAPE }

/** A sensor reading switches only this close to a quarter turn, so 45 degrees does not flicker. */
private const val SNAP_DEGREES = 30

/**
 * The turns [hold] allows, the preferred one first. [tall] is whether the natural orientation
 * is taller than wide: on a wide tablet, portrait is a quarter turn away.
 */
fun allowedTurns(hold: Hold, tall: Boolean): List<Int> = when (hold) {
    Hold.AUTO -> listOf(0, 1, 2, 3)
    Hold.PORTRAIT -> if (tall) listOf(0) else listOf(3, 1)
    Hold.LANDSCAPE -> if (tall) listOf(3, 1) else listOf(0)
}

/**
 * The turns for an OrientationEventListener reading: [degrees] clockwise, 0 in the natural
 * orientation, 90 with the left edge up, or -1 when flat or unknown. Keeps [current] when the
 * reading is not near a quarter turn or points to a turn [hold] does not allow.
 */
fun turnsFor(degrees: Int, current: Int, hold: Hold, tall: Boolean): Int {
    val allowed = allowedTurns(hold, tall)
    val keep = if (current in allowed) current else allowed.first()
    if (degrees < 0) return keep
    val quarter = (degrees + 45) / 90
    if (abs(degrees - quarter * 90) > SNAP_DEGREES) return keep
    val turns = (4 - quarter % 4) % 4
    return if (turns in allowed) turns else keep
}

/** The maze direction for [d], a direction as the player sees it (N is up as held). */
fun toMaze(d: Int, turns: Int): Int = DIRECTIONS[(DIRECTIONS.indexOf(d) + turns) % 4]

private val ARROWS = listOf(RemoteKey.UP, RemoteKey.RIGHT, RemoteKey.DOWN, RemoteKey.LEFT)

/** An arrow key as the player pressed it, turned into the arrow that steers that way on the maze. */
fun rotateKey(key: RemoteKey, turns: Int): RemoteKey {
    val i = ARROWS.indexOf(key)
    return if (i < 0) key else ARROWS[(i + turns) % 4]
}

/** The two toolbar strips: START is the top of a tall screen or the left of a wide one. */
enum class Strip { START, END }

/** The strip at the top as the player holds the phone, or in landscape the one at their left. */
fun toolbarStrip(turns: Int, tall: Boolean): Strip =
    if (tall) {
        if (turns <= 1) Strip.START else Strip.END
    } else {
        if (turns == 0 || turns == 3) Strip.START else Strip.END
    }
