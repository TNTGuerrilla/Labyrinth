// What BoardRenderer reads to draw a cell. The screensaver's Board and the game's Round
// both provide it, the way the desktop game's Round mirrors the attributes the
// screensaver's draw_cell reads.
package com.bydesigninteractive.labyrinth.maze

interface CellSource {
    val grid: Grid?
    val regionOf: Map<Cell, Int>
    val hues: DoubleArray
    val welds: Map<Edge, Double>
    /** Edge -> true while on the current route (bright), false once backed out of (dim). */
    val trail: Map<Edge, Boolean>
    val headCells: Set<Cell>
    val start: Cell?
    val end: Cell?
    val dot: Cell?
    /** While the dot glides into [dot]: the cell it left. Null when not gliding. */
    val glideFrom: Cell?
    /** The trail state the gliding edge had before this move, or null if it had none. */
    val glideOld: Boolean?
    /** How far the glide from [glideFrom] to [dot] has got: 0 to 1, and 1 at rest. */
    val glideProgress: Double
}
