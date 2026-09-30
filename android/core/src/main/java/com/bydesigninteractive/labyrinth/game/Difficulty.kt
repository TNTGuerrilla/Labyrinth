// Maze size presets and how big a maze is for the screen, ported from
// maze_game/difficulty.py. The size sets the number of cells on the maze's short side;
// the long side fills the screen's aspect ratio. The TV caps custom sizes at 200.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.fill
import kotlin.random.Random

val PRESETS: Map<String, Pair<Int, Int>> = linkedMapOf(
    "small" to (8 to 12), "medium" to (13 to 24), "large" to (25 to 48), "xl" to (49 to 96),
)
val SIZES = listOf("small", "medium", "large", "xl", "custom")
val SIZE_LABELS = mapOf("small" to "Small", "medium" to "Medium", "large" to "Large", "xl" to "XL", "custom" to "Custom")
const val MIN_CUSTOM = 4
const val MAX_CUSTOM = 200
/** Largest short side that still gives every cell at least 1 px at 100% zoom. */
fun ceiling(viewW: Int, viewH: Int, coverage: Int = 100): Int = maxOf(MIN_CUSTOM, fill(minOf(viewW, viewH), coverage))

fun sizeRange(size: String, customMin: Int, customMax: Int, cap: Int): Pair<Int, Int> {
    var (lo, hi) = if (size == "custom") minOf(customMin, customMax) to maxOf(customMin, customMax) else PRESETS.getValue(size)
    lo = maxOf(MIN_CUSTOM, minOf(lo, cap))
    hi = maxOf(lo, minOf(hi, cap))
    return lo to hi
}

fun pickShort(size: String, customMin: Int, customMax: Int, viewW: Int, viewH: Int, rng: Random, coverage: Int = 100): Int {
    val (lo, hi) = sizeRange(size, customMin, customMax, minOf(ceiling(viewW, viewH, coverage), MAX_CUSTOM))
    return rng.nextInt(lo, hi + 1)
}

/** (cols, rows) for a maze with [short] cells on its short side on this screen. */
fun gridSize(short: Int, viewW: Int, viewH: Int, coverage: Int = 100): Pair<Int, Int> {
    val shortFill = maxOf(1, fill(minOf(viewW, viewH), coverage))
    val longFill = fill(maxOf(viewW, viewH), coverage)
    val long = maxOf(short, longFill * short / shortFill)
    return if (viewW >= viewH) long to short else short to long
}
