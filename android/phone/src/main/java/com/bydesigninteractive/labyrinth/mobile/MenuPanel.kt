// The phone game's menu, drawn as ordinary views over the paused game: tabs across the top
// (they scroll sideways), then the tab's rows in a scrolling list. Numbers have a slider with
// - and + buttons, toggles a switch, choices a short list that opens under the row. Every
// control is focusable, so a controller or keyboard moves through it with the arrows and
// picks with OK. After a change only the shown values are refreshed, unless the rows
// themselves change (Custom adds two rows, for example), so focus and a dragged slider are
// not lost.
package com.bydesigninteractive.labyrinth.mobile

import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.view.View
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar
import android.widget.Switch
import com.bydesigninteractive.labyrinth.ACCENT
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.FOCUSED
import com.bydesigninteractive.labyrinth.TEXT
import com.bydesigninteractive.labyrinth.game.GameField
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.Kind
import com.bydesigninteractive.labyrinth.game.MenuAction
import com.bydesigninteractive.labyrinth.game.SIZES
import com.bydesigninteractive.labyrinth.game.SIZE_LABELS
import com.bydesigninteractive.labyrinth.game.adjust
import com.bydesigninteractive.labyrinth.game.toggle

private const val MAX_WIDTH_DP = 440
private const val WRAP = LinearLayout.LayoutParams.WRAP_CONTENT
private const val MATCH = LinearLayout.LayoutParams.MATCH_PARENT

class MenuPanel(context: Context, private val host: Host) : LinearLayout(context) {
    interface Host {
        val game: GameSettings
        val phone: PhoneSettings
        val version: String
        /** "Explored N . M:SS" while a maze is being played, else null. */
        fun readout(): String?
        fun changeGame(next: GameSettings)
        fun changePhone(next: PhoneSettings)
        /** Closes the menu and runs [action]. */
        fun runAction(action: MenuAction)
        fun openLink(link: MenuLink)
        fun close()
    }

    var tab = PhoneTab.PLAY
        private set
    private val tabRow = LinearLayout(context).apply { orientation = HORIZONTAL }
    private val tabScroll = HorizontalScrollView(context).apply {
        isHorizontalScrollBarEnabled = false
        addView(tabRow)
    }
    private val body = LinearLayout(context).apply { orientation = VERTICAL }
    private val bodyScroll = ScrollView(context).apply {
        isVerticalScrollBarEnabled = false
        addView(body)
    }
    private var rendered: List<MenuRow> = emptyList()
    private var expanded: MenuRow? = null
    /** Updates each shown value from the current settings; rebuilt with the rows. */
    private val refreshers = ArrayList<() -> Unit>()
    private var firstRow: View? = null

    init {
        orientation = VERTICAL
        setPadding(dp(16), dp(14), dp(16), dp(14))
        background = rounded(PANEL, dp(12).toFloat())
        isClickable = true // taps on the padding must not reach the scrim, which closes the menu
        val header = LinearLayout(context).apply {
            orientation = HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            addView(tabScroll, LayoutParams(0, WRAP, 1f))
            addView(context.panelButton("Close") { host.close() }.apply {
                textSize = 15f
                minHeight = dp(40)
            }, LayoutParams(WRAP, WRAP).apply { marginStart = dp(8) })
        }
        addView(header, LayoutParams(MATCH, WRAP))
        addView(bodyScroll, LayoutParams(MATCH, WRAP).apply { topMargin = dp(10) })
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val max = context.dp(MAX_WIDTH_DP)
        val w = if (MeasureSpec.getSize(widthMeasureSpec) > max) MeasureSpec.makeMeasureSpec(max, MeasureSpec.EXACTLY) else widthMeasureSpec
        super.onMeasure(w, heightMeasureSpec)
    }

    fun show(first: PhoneTab) {
        tab = first
        expanded = null
        render()
        bodyScroll.scrollTo(0, 0)
    }

    /** The shoulder buttons: the next or previous tab, wrapping around. */
    fun nextTab(step: Int) {
        val all = PhoneTab.entries
        show(all[(tab.ordinal + step + all.size) % all.size])
        focusFirst()
    }

    /** Where a controller's first arrow lands: the first control, or the current tab. */
    fun focusFirst() {
        (firstRow ?: tabRow.getChildAt(tab.ordinal))?.requestFocus()
    }

    /** After a setting changed: rebuild if the rows changed, else refresh the shown values. */
    fun changed() {
        if (rowsNow() != rendered) render() else refreshers.forEach { it() }
    }

    // Being clickable would press every child slider with the panel; they must not show as pressed.
    override fun dispatchSetPressed(pressed: Boolean) {}

    private fun rowsNow() = phoneRows(tab, host.game, host.phone, host.version)

    private fun setGame(next: GameSettings) {
        host.changeGame(next)
        changed()
    }

    private fun setPhone(next: PhoneSettings) {
        host.changePhone(next)
        changed()
    }

    private fun render() {
        val focusedTag = findFocus()?.tag
        renderTabs()
        body.removeAllViews()
        refreshers.clear()
        firstRow = null
        rendered = rowsNow()
        if (tab == PhoneTab.PLAY) host.readout()?.let { body.addView(note(it).apply { gravity = Gravity.CENTER }, LayoutParams(MATCH, WRAP)) }
        for (row in rendered) addRow(row)
        if (focusedTag != null) {
            val again = findViewWithTag<View>(focusedTag) ?: (focusedTag as? Pair<*, *>)?.first?.let { findViewWithTag<View>(it) }
            again?.requestFocus()
        }
    }

    private fun renderTabs() {
        tabRow.removeAllViews()
        for (t in PhoneTab.entries) {
            val current = t == tab
            tabRow.addView(context.label(t.title, 15f, if (current) ACCENT else DIM_TEXT).apply {
                setPadding(dp(12), dp(8), dp(12), dp(8))
                background = context.focusBackground(if (current) FOCUSED else Color.TRANSPARENT)
                isFocusable = true
                tag = t
                setOnClickListener { show(t) }
            })
        }
        tabScroll.post { tabRow.getChildAt(tab.ordinal)?.let { tabScroll.smoothScrollTo(maxOf(0, it.left - dp(24)), 0) } }
    }

    private fun addRow(row: MenuRow) {
        when (row) {
            is MenuRow.Note -> body.addView(note(row.text), LayoutParams(MATCH, WRAP))
            is MenuRow.Action -> addFocusable(context.panelButton(row.action.label) { host.runAction(row.action) }.apply { tag = row }, 8)
            is MenuRow.Link -> addFocusable(context.panelButton(row.link.label) { host.openLink(row.link) }.apply { tag = row }, 8)
            is MenuRow.Game -> when (row.field.kind) {
                Kind.TOGGLE -> toggleRow(row, row.field.label, { row.field.get(host.game) != 0.0 }) { setGame(toggle(host.game, row.field)) }
                Kind.NUMBER -> numberRow(row, row.field)
                Kind.CHOICE -> choiceRow(row, row.field.label, SIZES.map { SIZE_LABELS.getValue(it) }, { row.field.get(host.game).toInt() }) { i ->
                    setGame(row.field.set(host.game, i.toDouble()))
                }
            }
            is MenuRow.Choice -> choiceRow(row, row.choice.label, choiceOptions(row.choice), { choiceIndex(row.choice, host.phone) }) { i ->
                setPhone(choose(row.choice, host.phone, i))
            }
            is MenuRow.Toggle -> toggleRow(row, row.toggle.label, { toggleValue(row.toggle, host.phone) }) { setPhone(flip(row.toggle, host.phone)) }
        }
    }

    private fun addFocusable(view: View, topMarginDp: Int) {
        body.addView(view, LayoutParams(MATCH, WRAP).apply { topMargin = dp(topMarginDp) })
        if (firstRow == null) firstRow = view
    }

    /** A focusable, tappable line for a setting. */
    private fun rowLine(row: MenuRow) = LinearLayout(context).apply {
        orientation = HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        minimumHeight = dp(48)
        setPadding(dp(10), dp(6), dp(10), dp(6))
        background = context.focusBackground(Color.TRANSPARENT)
        isFocusable = true
        isClickable = true
        tag = row
    }

    private fun toggleRow(row: MenuRow, name: String, value: () -> Boolean, flip: () -> Unit) {
        @Suppress("DEPRECATION") // android.widget.Switch: this app does not use AndroidX
        val switch = Switch(context).apply {
            isClickable = false
            isFocusable = false
        }
        val line = rowLine(row).apply {
            addView(context.label(name, 17f, TEXT), LayoutParams(0, WRAP, 1f))
            addView(switch)
            setOnClickListener { flip() }
        }
        val refresh = { switch.isChecked = value() }
        refresh()
        refreshers += refresh
        addFocusable(line, 4)
    }

    private fun numberRow(row: MenuRow, f: GameField) {
        val value = context.label("", 17f, ACCENT)
        val head = LinearLayout(context).apply {
            orientation = HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(10), dp(10), dp(10), 0)
            addView(context.label(f.label, 17f, TEXT), LayoutParams(0, WRAP, 1f))
            addView(value)
        }
        val bar = SeekBar(context).apply {
            max = sliderSteps(f)
            keyProgressIncrement = 1
            isFocusable = true
            tag = row
            setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(seekBar: SeekBar, progress: Int, fromUser: Boolean) {
                    if (fromUser) setGame(setNumber(host.game, f, sliderValue(f, progress)))
                }

                override fun onStartTrackingTouch(seekBar: SeekBar) {}

                override fun onStopTrackingTouch(seekBar: SeekBar) {}
            })
        }
        val minus = context.panelButton("-") { setGame(adjust(host.game, f, -1, 0)) }.apply {
            minWidth = dp(48)
            tag = row to "-"
        }
        val plus = context.panelButton("+") { setGame(adjust(host.game, f, 1, 0)) }.apply {
            minWidth = dp(48)
            tag = row to "+"
        }
        val controls = LinearLayout(context).apply {
            orientation = HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(4), dp(2), dp(4), dp(6))
            addView(minus, LayoutParams(WRAP, WRAP))
            addView(bar, LayoutParams(0, WRAP, 1f))
            addView(plus, LayoutParams(WRAP, WRAP))
        }
        val refresh = {
            value.text = f.format(f.get(host.game))
            val step = sliderStep(f, f.get(host.game))
            if (bar.progress != step) bar.progress = step
        }
        refresh()
        refreshers += refresh
        body.addView(head, LayoutParams(MATCH, WRAP).apply { topMargin = dp(4) })
        body.addView(controls, LayoutParams(MATCH, WRAP))
        if (firstRow == null) firstRow = bar
    }

    private fun choiceRow(row: MenuRow, name: String, options: List<String>, index: () -> Int, pick: (Int) -> Unit) {
        val value = context.label("", 17f, ACCENT)
        val line = rowLine(row).apply {
            addView(context.label(name, 17f, TEXT), LayoutParams(0, WRAP, 1f))
            addView(value)
            setOnClickListener {
                expanded = if (expanded == row) null else row
                render()
            }
        }
        val refresh = { value.text = options.getOrElse(index()) { "" } }
        refresh()
        refreshers += refresh
        addFocusable(line, 4)
        if (expanded != row) return
        options.forEachIndexed { i, option ->
            val button = context.panelButton(option) {
                expanded = null
                pick(i)
                if (rowsNow() == rendered) render() // a changed row set was already rebuilt by pick
            }.apply {
                tag = row to i
                if (i == index()) setTextColor(ACCENT)
            }
            body.addView(button, LayoutParams(MATCH, WRAP).apply {
                topMargin = dp(4)
                marginStart = dp(24)
            })
        }
    }

    private fun note(text: String) = context.label(text, 14f, DIM_TEXT).apply {
        setPadding(dp(10), dp(8), dp(10), dp(4))
    }

    private fun dp(value: Int) = context.dp(value)
}
