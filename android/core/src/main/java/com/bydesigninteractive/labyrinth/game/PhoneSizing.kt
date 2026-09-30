// Maze sizes for phones, from the screen's physical size: each preset sets a cell size in
// millimetres on the maze's short side, so a 4K phone and a 1080p phone of the same size get
// the same maze. Pure; the phone game supplies its display's pixels per inch.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.fill
import kotlin.math.floor
import kotlin.math.roundToInt
import kotlin.random.Random

val CELL_MM: Map<String, Double> = linkedMapOf("small" to 8.0, "medium" to 5.0, "large" to 3.5, "xl" to 2.5)
const val MIN_CELL_MM = 1.5
/** A preset picks a short side within this fraction of its target, so mazes vary. */
const val PRESET_SPREAD = 0.15
const val MM_PER_INCH = 25.4
private const val MIN_PLAUSIBLE_PPI = 100f
private const val MAX_PLAUSIBLE_PPI = 1000f

/**
 * The display's pixels per inch: the average of the reported physical values, or the density
 * bucket when either is implausible (some devices report nonsense).
 */
fun plausiblePpi(reportedX: Float, reportedY: Float, densityDpi: Int): Double {
    fun ok(v: Float) = v in MIN_PLAUSIBLE_PPI..MAX_PLAUSIBLE_PPI
    return if (ok(reportedX) && ok(reportedY)) (reportedX + reportedY) / 2.0 else densityDpi.toDouble()
}

fun pxToMm(px: Int, ppi: Double): Double = px / ppi * MM_PER_INCH

/**
 * The range of cells on the short side of a maze whose short side is [shortMm] long. Never
 * smaller cells than MIN_CELL_MM, never more cells than [pixelCap] or MAX_CUSTOM, never fewer
 * than MIN_CUSTOM.
 */
fun phoneShortRange(size: String, customMin: Int, customMax: Int, shortMm: Double, pixelCap: Int): Pair<Int, Int> {
    val cap = maxOf(MIN_CUSTOM, minOf(floor(shortMm / MIN_CELL_MM).toInt(), pixelCap, MAX_CUSTOM))
    val (lo, hi) = if (size == "custom") {
        minOf(customMin, customMax) to maxOf(customMin, customMax)
    } else {
        val target = shortMm / CELL_MM.getValue(size)
        (target * (1 - PRESET_SPREAD)).roundToInt() to (target * (1 + PRESET_SPREAD)).roundToInt()
    }
    val low = lo.coerceIn(MIN_CUSTOM, cap)
    return low to hi.coerceIn(low, cap)
}

/** (cols, rows) for a new maze in a [viewW] x [viewH] pixel play area at [ppi]. */
fun phoneGrid(s: GameSettings, viewW: Int, viewH: Int, ppi: Double, rng: Random): Pair<Int, Int> {
    val shortMm = pxToMm(fill(minOf(viewW, viewH), s.coverage), ppi)
    val (lo, hi) = phoneShortRange(s.size, s.customMin, s.customMax, shortMm, ceiling(viewW, viewH, s.coverage))
    return gridSize(rng.nextInt(lo, hi + 1), viewW, viewH, s.coverage)
}
