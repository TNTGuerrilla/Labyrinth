// Small view helpers shared by the phone game's toolbar and panels.
package com.bydesigninteractive.labyrinth.mobile

import android.content.Context
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.StateListDrawable
import android.util.TypedValue
import android.view.Gravity
import android.widget.TextView
import com.bydesigninteractive.labyrinth.ACCENT
import com.bydesigninteractive.labyrinth.FOCUSED
import com.bydesigninteractive.labyrinth.TEXT

private val BUTTON = Color.rgb(34, 38, 46)

fun Context.dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

fun rounded(color: Int, radiusPx: Float, strokePx: Int = 0, strokeColor: Int = 0) = GradientDrawable().apply {
    setColor(color)
    cornerRadius = radiusPx
    if (strokePx > 0) setStroke(strokePx, strokeColor)
}

fun Context.label(value: String, sizeSp: Float, color: Int) = TextView(this).apply {
    text = value
    setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
    setTextColor(color)
}

/** A toolbar button. Not focusable, so a controller's arrows keep steering the dot. */
fun Context.chip(value: String, onClick: () -> Unit) = label(value, 14f, TEXT).apply {
    gravity = Gravity.CENTER
    maxLines = 1
    setPadding(dp(12), dp(8), dp(12), dp(8))
    background = rounded(FOCUSED, dp(8).toFloat())
    isFocusable = false
    setOnClickListener { onClick() }
}

/** A panel button: big enough for a thumb, and focusable so a controller or keyboard can pick it. */
fun Context.panelButton(value: String, onClick: () -> Unit) = label(value, 18f, TEXT).apply {
    gravity = Gravity.CENTER
    minHeight = dp(48)
    setPadding(dp(16), dp(10), dp(16), dp(10))
    isFocusable = true
    val radius = dp(10).toFloat()
    background = StateListDrawable().apply {
        addState(intArrayOf(android.R.attr.state_pressed), rounded(FOCUSED, radius))
        addState(intArrayOf(android.R.attr.state_focused), rounded(BUTTON, radius, dp(2), ACCENT))
        addState(intArrayOf(), rounded(BUTTON, radius))
    }
    setOnClickListener { onClick() }
}

/** Sizes a [chip] for the narrow vertical toolbar (or back for the horizontal one). */
fun TextView.compactChip(compact: Boolean) {
    setTextSize(TypedValue.COMPLEX_UNIT_SP, if (compact) 13f else 14f)
    val h = context.dp(if (compact) 6 else 12)
    setPadding(h, context.dp(8), h, context.dp(8))
}
