package com.bydesigninteractive.labyrinth.mobile

import android.content.Context
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import com.bydesigninteractive.labyrinth.ACCENT
import com.bydesigninteractive.labyrinth.BACKGROUND
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.play.formatTime

/**
 * The toolbar: cells explored and time, Hint and Menu. Across the top when the player holds
 * the phone so the strip runs sideways, or stacked in a column when the strip is at their side.
 */
class GameToolbar(context: Context, onHint: () -> Unit, onMenu: () -> Unit) : LinearLayout(context) {
    private val readout = context.label("", 14f, DIM_TEXT)
    private val hint = context.chip("Hint", onHint)
    private val menu = context.chip("Menu", onMenu)
    private var vertical: Boolean? = null
    private var explored: Int? = null
    private var elapsed = 0.0
    /** What the readout shows, so the 100 ms refresh only sets (and relayouts) a changed text. */
    private var shown = ""

    init {
        setBackgroundColor(BACKGROUND)
        setVertical(false)
    }

    fun setVertical(value: Boolean) {
        if (vertical == value) return
        vertical = value
        removeAllViews()
        val gap = context.dp(8)
        hint.compactChip(value)
        menu.compactChip(value)
        if (value) {
            orientation = VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(0, gap, 0, gap)
            readout.gravity = Gravity.CENTER
            addView(menu, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT))
            addView(hint, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT).apply { topMargin = gap })
            addView(View(context), LayoutParams(1, 0, 1f))
            addView(readout, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT))
        } else {
            orientation = HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(gap * 2, 0, gap, 0)
            readout.gravity = Gravity.START or Gravity.CENTER_VERTICAL
            addView(readout, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
            addView(hint, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT).apply { marginEnd = gap })
            addView(menu, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT))
        }
        shown = ""
        update()
    }

    /** A small dot after "Menu" while an update is on offer. */
    fun setBadge(on: Boolean) {
        val dot = if (on) GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(ACCENT)
            val size = context.dp(7)
            setSize(size, size)
            setBounds(0, 0, size, size)
        } else null
        menu.setCompoundDrawablesRelative(null, null, dot, null)
        menu.compoundDrawablePadding = context.dp(5)
    }

    /** [explored] is null while the maze grows (nothing to show yet). */
    fun show(explored: Int?, elapsed: Double) {
        this.explored = explored
        this.elapsed = elapsed
        update()
    }

    private fun update() {
        val e = explored
        val text = when {
            e == null -> ""
            vertical == true -> "${formatTime(elapsed)}\n$e"
            else -> "Explored $e \u00b7 ${formatTime(elapsed)}"
        }
        if (text != shown) {
            shown = text
            readout.text = text
        }
    }
}
