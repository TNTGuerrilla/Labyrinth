// Draws the remote test: the center box that flashes on each beat and the dot that
// reaches it exactly on the beat, from the side matching the button to press; or, for the
// sound step, a dot bouncing between two walls once per second.
package com.bydesigninteractive.labyrinth.play

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.os.SystemClock
import android.view.View
import com.bydesigninteractive.labyrinth.ACCENT
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.START_COLOR
import com.bydesigninteractive.labyrinth.game.BlockRun
import com.bydesigninteractive.labyrinth.game.RemoteKey
import kotlin.math.floor
import kotlin.math.min

private const val FLASH_MS = 90.0

class RemoteTestView(context: Context) : View(context) {
    private var run: BlockRun? = null
    private var syncStart = 0L
    private var syncing = false
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)

    fun showRun(r: BlockRun) {
        run = r
        syncing = false
        invalidate()
    }

    fun showSync(start: Long) {
        syncStart = start
        syncing = true
        run = null
        invalidate()
    }

    fun clear() {
        run = null
        syncing = false
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(Color.BLACK)
        val now = SystemClock.uptimeMillis().toDouble()
        run?.let { drawRun(canvas, it, now) }
        if (syncing) drawSync(canvas, now)
        if (run != null || syncing) postInvalidateOnAnimation()
    }

    private val unit get() = min(width, height).toFloat()
    private val cx get() = width / 2f
    private val cy get() = height * 0.62f

    private fun drawRun(canvas: Canvas, r: BlockRun, now: Double) {
        val half = unit * 0.06f
        val travel = unit * 0.3f
        val flashing = r.allBeats.any { now - it in 0.0..FLASH_MS }
        paint.style = if (flashing) Paint.Style.FILL else Paint.Style.STROKE
        paint.strokeWidth = unit * 0.006f
        paint.color = if (flashing) ACCENT else DIM_TEXT
        canvas.drawRect(cx - half, cy - half, cx + half, cy + half, paint)
        val i = r.allBeats.indexOfFirst { it >= now }
        if (i < 0) return
        val p = (1 - (r.allBeats[i] - now) / r.block.intervalMs).coerceIn(0.0, 1.0)
        val (dx, dy) = when (r.block.keyFor(i)) {
            RemoteKey.UP -> 0 to -1
            RemoteKey.DOWN -> 0 to 1
            RemoteKey.LEFT -> -1 to 0
            else -> 1 to 0 // Right, and OK, which comes in from the left
        }
        paint.style = Paint.Style.FILL
        paint.color = if (i < r.block.leadIn) DIM_TEXT else START_COLOR
        canvas.drawCircle(
            (cx - dx * (1 - p) * travel).toFloat(), (cy - dy * (1 - p) * travel).toFloat(), half * 0.5f, paint,
        )
    }

    private fun drawSync(canvas: Canvas, now: Double) {
        val travel = unit * 0.3f
        val left = cx - travel
        val right = cx + travel
        val t = (now - syncStart) / 1000.0
        val k = floor(t).toInt()
        val hitFlash = t >= 1 && (t - k) * 1000 < FLASH_MS
        paint.style = Paint.Style.FILL
        for ((x, isRight) in listOf(left to false, right to true)) {
            val lit = hitFlash && (k % 2 == 1) == isRight
            paint.color = if (lit) ACCENT else DIM_TEXT
            canvas.drawRect(x - unit * 0.006f, cy - unit * 0.1f, x + unit * 0.006f, cy + unit * 0.1f, paint)
        }
        val frac = if (t < 0) 0.0 else t - k
        val x = if (t < 0 || k % 2 == 0) left + frac * (right - left) else right - frac * (right - left)
        paint.color = START_COLOR
        canvas.drawCircle(x.toFloat(), cy, unit * 0.03f, paint)
    }
}
