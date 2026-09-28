// Draws a Board's changed cells onto a Canvas, ported from maze_saver/render.py.
//
// Each cell is redrawn from scratch: half-pipes ("spokes") run from the cell's center to
// the middle of each open side, so neighboring cells join seamlessly.
package com.bydesigninteractive.labyrinth

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import com.bydesigninteractive.labyrinth.maze.Board
import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Changes
import com.bydesigninteractive.labyrinth.maze.DIRECTIONS
import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import com.bydesigninteractive.labyrinth.maze.edgeKey
import kotlin.math.roundToInt

private val START_COLOR = Color.rgb(60, 220, 90)
private val END_COLOR = Color.rgb(235, 64, 64)
private val TRAIL_COLOR = Color.rgb(255, 240, 205)
private val TRAIL_DIM_COLOR = Color.rgb(80, 80, 80)
private val WELD_COLOR = Color.rgb(255, 255, 255)

private const val PIPE_WIDTH = 0.40 // fraction of the cell size
private const val STRIPE_RATIO = 1.0 / 3 // fraction of the pipe width
private const val TRAIL_WIDTH = 0.15
private const val MARKER_RADIUS = 0.275
private const val DOT_AT_END_SCALE = 0.7

/** (outer pipe, center stripe, growing head) colors for a hue. */
private class Palette(hue: Double) {
    val outer = hsv(hue, 0.60f, 0.55f)
    val stripe = hsv(hue, 0.40f, 0.85f)
    val head = hsv(hue, 0.25f, 1.0f)

    private fun hsv(h: Double, s: Float, v: Float): Int = Color.HSVToColor(floatArrayOf((h * 360).toFloat(), s, v))
}

class BoardRenderer {
    private val palettes = HashMap<Double, Palette>()
    private val rectPaint = Paint().apply { style = Paint.Style.FILL }
    private val circlePaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val scratch = Rect()

    /**
     * Draws the changes and returns the rectangle of each redrawn cell. A clear blacks out
     * the whole canvas first; that area is not in the list, since changes.clear reports it.
     */
    fun apply(canvas: Canvas, board: Board, changes: Changes): List<Rect> {
        if (changes.clear) {
            canvas.drawColor(Color.BLACK)
            palettes.clear()
        }
        val geo = board.geometry ?: return emptyList()
        return changes.cells.map { c ->
            val left = geo.cellLeft(c)
            val top = geo.cellTop(c)
            drawCell(canvas, board, c, left, top, geo.cell)
            Rect(left, top, left + geo.cell, top + geo.cell)
        }
    }

    private fun drawCell(canvas: Canvas, board: Board, c: Cell, left: Int, top: Int, size: Int) {
        canvas.save()
        canvas.clipRect(left, top, left + size, top + size)
        rectPaint.color = Color.BLACK
        canvas.drawRect(left.toFloat(), top.toFloat(), (left + size).toFloat(), (top + size).toFloat(), rectPaint)
        val region = board.regionOf[c]
        if (region != null) {
            val palette = palettes.getOrPut(board.hues[region]) { Palette(board.hues[region]) }
            drawPipe(canvas, board, c, left, top, size, palette)
        }
        drawTrail(canvas, board, c, left, top, size)
        drawMarkers(canvas, board, c, left, top, size)
        canvas.restore()
    }

    /** The half-pipe from the cell's center toward side d, `width` pixels thick. */
    private fun spoke(left: Int, top: Int, size: Int, d: Int, width: Int): Rect {
        val cx = left + size / 2
        val cy = top + size / 2
        val half = width / 2
        return when (d) {
            N -> scratch.apply { set(cx - half, top, cx - half + width, cy) }
            S -> scratch.apply { set(cx - half, cy, cx - half + width, top + size) }
            W -> scratch.apply { set(left, cy - half, cx, cy - half + width) }
            else -> scratch.apply { set(cx, cy - half, left + size, cy - half + width) }
        }
    }

    private fun fillSpoke(canvas: Canvas, left: Int, top: Int, size: Int, d: Int, width: Int, color: Int) {
        rectPaint.color = color
        canvas.drawRect(spoke(left, top, size, d, width), rectPaint)
    }

    /**
     * Fills the piece of a spoke between fractions [near] and [far] of the way from the
     * cell's center (0) to its side (1).
     */
    private fun fillSpokePart(
        canvas: Canvas, left: Int, top: Int, size: Int, d: Int, width: Int, near: Double, far: Double, color: Int,
    ) {
        val full = Rect(spoke(left, top, size, d, width))
        val length = if (d == N || d == S) full.height() else full.width()
        val a = (length * near).roundToInt()
        val b = (length * far).roundToInt()
        when (d) {
            N -> full.set(full.left, full.bottom - b, full.right, full.bottom - a)
            S -> full.set(full.left, full.top + a, full.right, full.top + b)
            W -> full.set(full.right - b, full.top, full.right - a, full.bottom)
            else -> full.set(full.left + a, full.top, full.left + b, full.bottom)
        }
        rectPaint.color = color
        canvas.drawRect(full, rectPaint)
    }

    /** A filled circle at the cell center, lined up with spokes `alignWidth` pixels wide. */
    private fun centerCircle(canvas: Canvas, left: Int, top: Int, size: Int, radius: Float, color: Int, alignWidth: Int) {
        val shift = if (alignWidth % 2 == 1) 0.5f else 0f
        circlePaint.style = Paint.Style.FILL
        circlePaint.color = color
        canvas.drawCircle(left + size / 2 + shift, top + size / 2 + shift, radius, circlePaint)
    }

    private fun drawPipe(canvas: Canvas, board: Board, c: Cell, left: Int, top: Int, size: Int, colors: Palette) {
        val pipeW = maxOf(2, (size * PIPE_WIDTH).roundToInt())
        val stripeW = maxOf(1, (pipeW * STRIPE_RATIO).roundToInt())
        val bits = board.grid!!.openDirs(c)
        val dirs = DIRECTIONS.filter { bits and it != 0 }
        val welding = dirs.filter { edgeKey(c, c.step(it)) in board.welds }.toSet()
        for (d in dirs) {
            fillSpoke(canvas, left, top, size, d, pipeW, if (d in welding) WELD_COLOR else colors.outer)
        }
        centerCircle(canvas, left, top, size, (pipeW / 2).toFloat(), colors.outer, pipeW)
        for (d in dirs) {
            if (d !in welding) fillSpoke(canvas, left, top, size, d, stripeW, colors.stripe)
        }
        centerCircle(canvas, left, top, size, maxOf(1, stripeW / 2).toFloat(), colors.stripe, stripeW)
        if (c in board.heads.values) {
            val r = maxOf(2, pipeW / 2 + maxOf(1, size / 20))
            centerCircle(canvas, left, top, size, r.toFloat(), colors.head, pipeW)
        }
    }

    private fun trailColor(state: Boolean): Int = if (state) TRAIL_COLOR else TRAIL_DIM_COLOR

    private fun drawTrail(canvas: Canvas, board: Board, c: Cell, left: Int, top: Int, size: Int) {
        val trailW = maxOf(1, (size * TRAIL_WIDTH).roundToInt())
        val glideFrom = board.glideFrom
        val moving = glideFrom?.let { edgeKey(it, board.dot!!) }
        val p = board.glideProgress
        var any = false
        var anyBright = false
        for (d in DIRECTIONS) {
            val key = edgeKey(c, c.step(d))
            val state = board.trail[key] ?: continue
            if (key != moving) {
                fillSpoke(canvas, left, top, size, d, trailW, trailColor(state))
                any = true
                anyBright = anyBright || state
                continue
            }
            // The edge the dot is gliding along: its new state only reaches as far as the
            // dot, and the old state (if any) still shows ahead of it. Along the edge, t runs
            // from glideFrom's center (0) to the dot cell's center (1); each cell holds half.
            val old = board.glideOld
            if (c == glideFrom) {
                val reach = minOf(1.0, 2 * p) // new state from the center out to the dot
                fillSpokePart(canvas, left, top, size, d, trailW, 0.0, reach, trailColor(state))
                if (old != null && reach < 1) fillSpokePart(canvas, left, top, size, d, trailW, reach, 1.0, trailColor(old))
                any = true
                anyBright = anyBright || state
            } else {
                val reach = maxOf(0.0, 2 * p - 1) // new state from the side in toward the center
                if (reach > 0) fillSpokePart(canvas, left, top, size, d, trailW, 1 - reach, 1.0, trailColor(state))
                if (old != null && reach < 1) fillSpokePart(canvas, left, top, size, d, trailW, 0.0, 1 - reach, trailColor(old))
                if (old != null) {
                    any = true
                    anyBright = anyBright || old
                }
            }
        }
        if (any) {
            val color = if (anyBright) TRAIL_COLOR else TRAIL_DIM_COLOR
            centerCircle(canvas, left, top, size, maxOf(1, trailW / 2).toFloat(), color, trailW)
        }
    }

    private fun drawMarkers(canvas: Canvas, board: Board, c: Cell, left: Int, top: Int, size: Int) {
        val radius = maxOf(2, (size * MARKER_RADIUS).roundToInt())
        val glideFrom = board.glideFrom
        if (c == board.end) centerCircle(canvas, left, top, size, radius.toFloat(), END_COLOR, 1)
        if (c == board.start) {
            if (board.dot == null || (board.dot == board.start && glideFrom == null)) {
                centerCircle(canvas, left, top, size, radius.toFloat(), START_COLOR, 1)
            } else {
                val ring = maxOf(1, radius / 3).toFloat()
                circlePaint.style = Paint.Style.STROKE
                circlePaint.strokeWidth = ring
                circlePaint.color = START_COLOR
                canvas.drawCircle(left + size / 2 + 0.5f, top + size / 2 + 0.5f, radius - ring / 2, circlePaint)
            }
        }
        val dot = board.dot ?: return
        // The gliding dot can straddle both cells, so each draws its part (the canvas is
        // clipped to the cell); at rest, the start marker stands in for the dot.
        val gliding = glideFrom != null && (c == glideFrom || c == dot)
        if (!gliding && (c != dot || c == board.start)) return
        val p = board.glideProgress
        var dotRadius = radius.toDouble()
        if (dot == board.end) dotRadius = maxOf(1.0, radius * (1 - (1 - DOT_AT_END_SCALE) * p))
        // How many cells c's center lies ahead of the dot, back along the glide.
        val back = if (glideFrom == null) 0.0 else if (c == dot) 1 - p else -p
        val dx = if (glideFrom == null) 0 else dot.x - glideFrom.x
        val dy = if (glideFrom == null) 0 else dot.y - glideFrom.y
        circlePaint.style = Paint.Style.FILL
        circlePaint.color = START_COLOR
        canvas.drawCircle(
            (left + size / 2 + 0.5 - dx * size * back).toFloat(),
            (top + size / 2 + 0.5 - dy * size * back).toFloat(),
            dotRadius.toFloat(), circlePaint,
        )
    }
}
