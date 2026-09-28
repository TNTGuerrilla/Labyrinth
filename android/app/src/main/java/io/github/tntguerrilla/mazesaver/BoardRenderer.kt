// Draws a Board's changed cells onto a Canvas, ported from maze_saver/render.py.
//
// Each cell is redrawn from scratch: half-pipes ("spokes") run from the cell's center to
// the middle of each open side, so neighboring cells join seamlessly.
package io.github.tntguerrilla.mazesaver

import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import io.github.tntguerrilla.mazesaver.maze.Board
import io.github.tntguerrilla.mazesaver.maze.Cell
import io.github.tntguerrilla.mazesaver.maze.Changes
import io.github.tntguerrilla.mazesaver.maze.DIRECTIONS
import io.github.tntguerrilla.mazesaver.maze.E
import io.github.tntguerrilla.mazesaver.maze.N
import io.github.tntguerrilla.mazesaver.maze.S
import io.github.tntguerrilla.mazesaver.maze.W
import io.github.tntguerrilla.mazesaver.maze.edgeKey
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

    /** Draws the changes and returns the area touched, or null if nothing was drawn. */
    fun apply(canvas: Canvas, board: Board, changes: Changes): Rect? {
        var dirty: Rect? = null
        if (changes.clear) {
            canvas.drawColor(Color.BLACK)
            dirty = Rect(0, 0, canvas.width, canvas.height)
            palettes.clear()
        }
        val geo = board.geometry ?: return dirty
        for (c in changes.cells) {
            val left = geo.cellLeft(c)
            val top = geo.cellTop(c)
            drawCell(canvas, board, c, left, top, geo.cell)
            val cellRect = Rect(left, top, left + geo.cell, top + geo.cell)
            if (dirty == null) dirty = cellRect else dirty.union(cellRect)
        }
        return dirty
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

    private fun drawTrail(canvas: Canvas, board: Board, c: Cell, left: Int, top: Int, size: Int) {
        val trailW = maxOf(1, (size * TRAIL_WIDTH).roundToInt())
        var any = false
        var anyBright = false
        for (d in DIRECTIONS) {
            val state = board.trail[edgeKey(c, c.step(d))] ?: continue
            fillSpoke(canvas, left, top, size, d, trailW, if (state) TRAIL_COLOR else TRAIL_DIM_COLOR)
            any = true
            anyBright = anyBright || state
        }
        if (any) {
            val color = if (anyBright) TRAIL_COLOR else TRAIL_DIM_COLOR
            centerCircle(canvas, left, top, size, maxOf(1, trailW / 2).toFloat(), color, trailW)
        }
    }

    private fun drawMarkers(canvas: Canvas, board: Board, c: Cell, left: Int, top: Int, size: Int) {
        val radius = maxOf(2, (size * MARKER_RADIUS).roundToInt())
        if (c == board.end) centerCircle(canvas, left, top, size, radius.toFloat(), END_COLOR, 1)
        if (c == board.start) {
            if (board.dot == null || board.dot == board.start) {
                centerCircle(canvas, left, top, size, radius.toFloat(), START_COLOR, 1)
            } else {
                val ring = maxOf(1, radius / 3).toFloat()
                circlePaint.style = Paint.Style.STROKE
                circlePaint.strokeWidth = ring
                circlePaint.color = START_COLOR
                canvas.drawCircle(left + size / 2 + 0.5f, top + size / 2 + 0.5f, radius - ring / 2, circlePaint)
            }
        }
        if (c == board.dot && c != board.start) {
            val dotRadius = if (c == board.end) maxOf(1, (radius * DOT_AT_END_SCALE).roundToInt()) else radius
            centerCircle(canvas, left, top, size, dotRadius.toFloat(), START_COLOR, 1)
        }
    }
}
