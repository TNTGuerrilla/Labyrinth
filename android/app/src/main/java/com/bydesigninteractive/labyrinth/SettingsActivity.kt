// The app's launcher screen: screensaver settings, built for a TV remote. Up and down move
// between rows, left and right change the focused value (hold to speed up), and changes
// save as they are made. Also opened from the system screensaver settings, when a TV shows them.
package com.bydesigninteractive.labyrinth

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.StateListDrawable
import android.os.Bundle
import android.provider.Settings.Secure
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bydesigninteractive.labyrinth.maze.Field
import com.bydesigninteractive.labyrinth.maze.Settings

private val BACKGROUND = Color.rgb(16, 18, 22)
private val FOCUSED = Color.rgb(52, 58, 70)
private val TEXT = Color.rgb(230, 230, 230)
private val DIM_TEXT = Color.rgb(150, 150, 150)
private val ACCENT = Color.rgb(60, 220, 90)

class SettingsActivity : Activity() {
    private lateinit var settings: Settings
    private val valueViews = HashMap<Field, TextView>()
    private lateinit var help: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = SettingsStore.load(this)

        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(64), dp(40), dp(64), dp(40))
        }
        column.addView(text("Labyrinth", 30f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(16), 0, dp(16), dp(16))
        })
        var first: View? = null
        for (field in Field.entries) {
            val row = fieldRow(field)
            column.addView(row)
            if (first == null) first = row
        }
        column.addView(button("Preview screensaver") { startActivity(Intent(this, PreviewActivity::class.java)) })
        column.addView(button("Reset to defaults") { update(Settings()) })
        help = text("", 15f, DIM_TEXT).apply { setPadding(dp(16), dp(24), dp(16), 0) }
        column.addView(help)

        setContentView(ScrollView(this).apply {
            setBackgroundColor(BACKGROUND)
            addView(column)
        })
        refresh()
        first?.requestFocus()
    }

    override fun onResume() {
        super.onResume()
        // Refreshed here so the status is current after running the ADB command.
        help.text = setupHelp()
    }

    private fun fieldRow(field: Field): LinearLayout {
        val value = text("", 20f, ACCENT).apply {
            gravity = Gravity.END
            typeface = Typeface.MONOSPACE
        }
        valueViews[field] = value
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(10), dp(16), dp(10))
            isFocusable = true
            background = focusBackground()
            addView(text(field.label, 20f, TEXT), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(value)
            setOnKeyListener { _, keyCode, event ->
                val sign = when (keyCode) {
                    KeyEvent.KEYCODE_DPAD_LEFT -> -1
                    KeyEvent.KEYCODE_DPAD_RIGHT -> 1
                    else -> return@setOnKeyListener false
                }
                if (event.action == KeyEvent.ACTION_DOWN) adjust(field, sign, event.repeatCount)
                true
            }
        }
    }

    /** Steps the field by its increment, faster the longer the button is held. */
    private fun adjust(field: Field, sign: Int, repeatCount: Int) {
        val multiplier = when {
            repeatCount >= 20 -> 10
            repeatCount >= 8 -> 5
            else -> 1
        }
        val value = (field.get(settings) + sign * field.increment * multiplier).coerceIn(field.low, field.high)
        var next = field.set(settings, value)
        // Keep min <= max by pushing the other bound along.
        if (field == Field.MIN_CELLS && next.minCells > next.maxCells) next = next.copy(maxCells = next.minCells)
        if (field == Field.MAX_CELLS && next.maxCells < next.minCells) next = next.copy(minCells = next.maxCells)
        update(next)
    }

    private fun update(next: Settings) {
        settings = next
        SettingsStore.save(this, next)
        refresh()
    }

    private fun refresh() {
        for ((field, view) in valueViews) view.text = "<  ${field.format(field.get(settings))}  >"
    }

    private fun button(label: String, onClick: () -> Unit): TextView =
        text(label, 20f, TEXT).apply {
            setPadding(dp(16), dp(12), dp(16), dp(12))
            isFocusable = true
            isClickable = true
            background = focusBackground()
            setOnClickListener { onClick() }
        }

    private fun setupHelp(): String {
        val component = "$packageName/.LabyrinthDreamService"
        val active = try {
            if (Secure.getString(contentResolver, "screensaver_components")?.contains(component) == true) {
                "Labyrinth is the current screensaver."
            } else {
                "Labyrinth is not the current screensaver yet."
            }
        } catch (_: SecurityException) {
            null
        }
        return listOfNotNull(
            active,
            "To make it the screensaver, run this once from a computer connected with ADB:",
            "adb shell settings put secure screensaver_components $component",
            "On TCL TVs, also allow Auto Launch for this app so it can start when the TV is idle.",
        ).joinToString("\n\n")
    }

    private fun text(value: String, sizeSp: Float, color: Int) = TextView(this).apply {
        text = value
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
        setTextColor(color)
    }

    private fun focusBackground() = StateListDrawable().apply {
        addState(intArrayOf(android.R.attr.state_focused), GradientDrawable().apply {
            setColor(FOCUSED)
            cornerRadius = dp(8).toFloat()
        })
        addState(intArrayOf(), GradientDrawable().apply { setColor(Color.TRANSPARENT) })
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
