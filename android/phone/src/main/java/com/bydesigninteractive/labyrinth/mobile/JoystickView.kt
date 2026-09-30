// The touch joystick: a translucent disc cut into four wedges, drawn and touched in the
// player's frame (it lives in the turned overlay). [onChange] hears each change of wedge, as a
// direction the player sees (N is up as held), or null when the thumb lifts or rests in the
// middle.
package com.bydesigninteractive.labyrinth.mobile

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.os.Build
import android.view.MotionEvent
import android.view.View
import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.touch.JOYSTICK_DEAD_ZONE
import com.bydesigninteractive.labyrinth.touch.wedge
import kotlin.math.min

class JoystickView(context: Context, private val onChange: (Int?) -> Unit) : View(context) {
    private var active: Int? = null
    private var armed = false
    private var pointerId = -1
    private val disc = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(60, 255, 255, 255) }
    private val lit = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.argb(120, 60, 220, 90) }
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(120, 0, 0, 0)
        style = Paint.Style.STROKE
        strokeWidth = context.dp(2).toFloat()
    }

    /** Lets go without telling anyone: the game already forgot its held keys. */
    fun reset() {
        armed = false
        active = null
        invalidate()
    }

    override fun onLayout(changed: Boolean, left: Int, top: Int, right: Int, bottom: Int) {
        super.onLayout(changed, left, top, right, bottom)
        // A thumb on the joystick near the screen edge must not become Android's back gesture.
        if (Build.VERSION.SDK_INT >= 29) systemGestureExclusionRects = listOf(Rect(0, 0, width, height))
    }

    override fun onDraw(canvas: Canvas) {
        val r = min(width, height) / 2f - line.strokeWidth
        val cx = width / 2f
        val cy = height / 2f
        canvas.drawCircle(cx, cy, r, disc)
        active?.let { d ->
            val start = when (d) {
                N -> 225f
                E -> 315f
                S -> 45f
                else -> 135f
            }
            canvas.drawArc(cx - r, cy - r, cx + r, cy + r, start, 90f, true, lit)
        }
        val k = r * 0.7071f
        canvas.drawLine(cx - k, cy - k, cx + k, cy + k, line)
        canvas.drawLine(cx - k, cy + k, cx + k, cy - k, line)
        canvas.drawCircle(cx, cy, r * JOYSTICK_DEAD_ZONE, line)
        canvas.drawCircle(cx, cy, r, line)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        val next: Int?
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                armed = true
                pointerId = event.getPointerId(0)
                next = wedge(event.x - width / 2f, event.y - height / 2f, min(width, height) / 2f)
            }
            MotionEvent.ACTION_MOVE -> {
                if (!armed) return true
                val i = event.findPointerIndex(pointerId)
                if (i == -1) return true
                next = wedge(event.getX(i) - width / 2f, event.getY(i) - height / 2f, min(width, height) / 2f)
            }
            MotionEvent.ACTION_POINTER_DOWN -> return true
            MotionEvent.ACTION_POINTER_UP -> {
                if (!armed || event.getPointerId(event.actionIndex) != pointerId) return true
                next = null
            }
            else -> next = null
        }
        if (!armed) return true
        if (next != active) {
            active = next
            invalidate()
            onChange(next)
        }
        return true
    }
}
