// Zoom and scroll for the game, ported from maze_game/camera.py.
//
// Positions are in cell units: cell (x, y) spans x..x+1 and y..y+1. Pixels are relative to
// the screen's top-left corner. Cell size is a whole number of pixels.
package com.bydesigninteractive.labyrinth.game

import kotlin.math.roundToInt

const val MAX_CELL_PX = 96 // twice the desktop's 48: a TV is watched from the couch
const val ZOOM_STEP = 1.25
const val FOLLOW_RATE = 8.0 // how quickly the camera catches up, per second

/** At 100% zoom the maze fits into [coverage] percent of the screen. */
class Camera(val cols: Int, val rows: Int, viewW: Int, viewH: Int, val coverage: Int = 100) {
    var viewW = 1
        private set
    var viewH = 1
        private set
    var fitPx = 1
        private set
    var cellPx = 1
        private set
    var cx = cols / 2.0
        private set
    var cy = rows / 2.0
        private set

    init {
        resize(viewW, viewH)
    }

    /** New screen size; keeps the zoom ratio. */
    fun resize(w: Int, h: Int) {
        val ratio = cellPx.toDouble() / fitPx
        viewW = maxOf(1, w)
        viewH = maxOf(1, h)
        fitPx = maxOf(1, minOf(viewW * coverage / 100.0 / cols, viewH * coverage / 100.0 / rows).toInt())
        cellPx = clampPx((fitPx * ratio).roundToInt())
        clampCenter()
    }

    val maxPx: Int get() = maxOf(fitPx, MAX_CELL_PX)
    val zoom: Double get() = cellPx.toDouble() / fitPx
    val zoomed: Boolean get() = cellPx > fitPx

    private fun clampPx(px: Int): Int = px.coerceIn(fitPx, maxPx)

    /** Pixel position of cell-space (0, 0). */
    fun origin(): Pair<Int, Int> =
        (viewW / 2.0 - cx * cellPx).roundToInt() to (viewH / 2.0 - cy * cellPx).roundToInt()

    fun toScreen(x: Double, y: Double): Pair<Double, Double> {
        val (ox, oy) = origin()
        return (ox + x * cellPx) to (oy + y * cellPx)
    }

    /** Zoom in (steps > 0) or out, keeping [anchor] at the same pixel position. */
    fun zoomBy(steps: Int, anchor: Pair<Double, Double>) {
        var next = cellPx
        repeat(Math.abs(steps)) {
            var n = if (steps > 0) (next * ZOOM_STEP).roundToInt() else (next / ZOOM_STEP).roundToInt()
            if (n == next) n += if (steps > 0) 1 else -1
            next = clampPx(n)
        }
        if (next == cellPx) return
        val (sx, sy) = toScreen(anchor.first, anchor.second)
        cellPx = next
        cx = anchor.first - (sx - viewW / 2.0) / next
        cy = anchor.second - (sy - viewH / 2.0) / next
        clampCenter()
    }

    fun resetZoom() {
        cellPx = fitPx
        clampCenter()
    }

    /** Ease the view toward [pos], clamped to the maze. Fixed at 100% zoom. */
    fun follow(pos: Pair<Double, Double>, dt: Double) {
        if (!zoomed) return
        val k = minOf(1.0, dt * FOLLOW_RATE)
        cx += (pos.first - cx) * k
        cy += (pos.second - cy) * k
        clampCenter()
    }

    private fun clampCenter() {
        if (!zoomed) {
            cx = cols / 2.0
            cy = rows / 2.0
            return
        }
        val hw = viewW / 2.0 / cellPx
        val hh = viewH / 2.0 / cellPx
        cx = minOf(maxOf(cx, minOf(hw, cols / 2.0)), maxOf(cols - hw, cols / 2.0))
        cy = minOf(maxOf(cy, minOf(hh, rows / 2.0)), maxOf(rows - hh, rows / 2.0))
    }
}
