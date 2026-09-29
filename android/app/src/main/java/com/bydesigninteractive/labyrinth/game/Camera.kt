// Zoom and scroll for the game, ported from maze_game/camera.py.
//
// Positions are in cell units: cell (x, y) spans x..x+1 and y..y+1. Pixels are relative to
// the screen's top-left corner. Cell size is a whole number of pixels.
package com.bydesigninteractive.labyrinth.game

import kotlin.math.roundToInt

const val CAMERA_FILL = 0.8 // 100% zoom fits the maze into 80% of the screen
const val MAX_CELL_PX = 96 // twice the desktop's 48: a TV is watched from the couch
const val ZOOM_STEP = 1.25
const val FOLLOW_ZONE = 0.4 // the dot stays inside the central 40% of the view
const val FOLLOW_RATE = 8.0 // how quickly the camera catches up, per second

class Camera(val cols: Int, val rows: Int, viewW: Int, viewH: Int) {
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
        fitPx = maxOf(1, minOf(viewW * CAMERA_FILL / cols, viewH * CAMERA_FILL / rows).toInt())
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

    /** Ease the view so [pos] stays inside the central zone. Fixed at 100% zoom. */
    fun follow(pos: Pair<Double, Double>, dt: Double) {
        if (!zoomed) return
        val hw = viewW * FOLLOW_ZONE / 2 / cellPx
        val hh = viewH * FOLLOW_ZONE / 2 / cellPx
        val tx = minOf(maxOf(cx, pos.first - hw), pos.first + hw)
        val ty = minOf(maxOf(cy, pos.second - hh), pos.second + hh)
        val k = minOf(1.0, dt * FOLLOW_RATE)
        cx += (tx - cx) * k
        cy += (ty - cy) * k
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
