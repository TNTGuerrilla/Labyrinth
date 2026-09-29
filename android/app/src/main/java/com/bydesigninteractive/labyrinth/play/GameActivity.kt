// The game screen. Remote keys go through GameInput; the resulting commands drive the game
// on GameView's render thread or the menu here. The menu, the readout, the win panel and the
// "Press Back again" note are ordinary Views over the GL surface. A 100 ms tick reads the
// render thread's snapshot to update them and to hold the screen on only while the dot moves.
package com.bydesigninteractive.labyrinth.play

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import com.bydesigninteractive.labyrinth.ACCENT
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.FOCUSED
import com.bydesigninteractive.labyrinth.TEXT
import com.bydesigninteractive.labyrinth.game.Command
import com.bydesigninteractive.labyrinth.game.GameInput
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.InputState
import com.bydesigninteractive.labyrinth.game.Kind
import com.bydesigninteractive.labyrinth.game.MenuAction
import com.bydesigninteractive.labyrinth.game.MenuEffect
import com.bydesigninteractive.labyrinth.game.MenuModel
import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.game.RoundPhase
import com.bydesigninteractive.labyrinth.game.Row
import com.bydesigninteractive.labyrinth.game.Tab
import com.bydesigninteractive.labyrinth.game.needsNewMaze
import com.bydesigninteractive.labyrinth.game.rows
import com.bydesigninteractive.labyrinth.game.selectable

private const val TICK_MS = 100L
private const val BACK_HINT_MS = 2000L
private val PANEL = Color.argb(240, 16, 18, 22)
private val WARN = Color.rgb(235, 170, 60)

fun formatTime(seconds: Double): String {
    val s = seconds.toInt()
    return "%d:%02d".format(s / 60, s % 60)
}

class GameActivity : Activity() {
    private lateinit var view: GameView
    private lateinit var settings: GameSettings
    private lateinit var remote: RemoteProfile
    private var testing = false
    private val input = GameInput()
    private val menu = MenuModel()
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var readout: TextView
    private lateinit var menuPanel: LinearLayout
    private lateinit var winPanel: LinearLayout
    private lateinit var backHint: TextView
    private var menuSettingsBefore: GameSettings? = null
    private var winShown = false
    /** The panel was just dismissed; ignore stale win snapshots until one without winScreen arrives. */
    private var winDismissed = false
    private var screenHeld = false
    private var away = false

    private val tick = object : Runnable {
        override fun run() {
            refresh()
            handler.postDelayed(this, TICK_MS)
        }
    }
    private val hideBackHint = Runnable { backHint.visibility = View.GONE }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = GameStore.load(this)
        val firstOfSession = !Session.controlsShown
        Session.controlsShown = true
        remote = GameStore.loadRemote(this) ?: RemoteProfile()
        view = GameView(this, settings, remote, startPaused = firstOfSession)
        view.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY

        readout = text("", 16f, DIM_TEXT)
        menuPanel = panel()
        winPanel = panel()
        backHint = text("Press Back again to leave", 18f, TEXT).apply {
            setPadding(dp(20), dp(10), dp(20), dp(10))
            background = rounded(PANEL)
            visibility = View.GONE
        }
        val root = FrameLayout(this)
        root.addView(view)
        root.addView(readout, FrameLayout.LayoutParams(WRAP, WRAP, Gravity.TOP or Gravity.END).apply {
            setMargins(0, dp(16), dp(24), 0)
        })
        root.addView(menuPanel, FrameLayout.LayoutParams(dp(640), WRAP, Gravity.CENTER))
        root.addView(winPanel, FrameLayout.LayoutParams(dp(420), WRAP, Gravity.CENTER))
        root.addView(backHint, FrameLayout.LayoutParams(WRAP, WRAP, Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply {
            bottomMargin = dp(40)
        })
        setContentView(root)
        menuPanel.visibility = View.GONE
        winPanel.visibility = View.GONE
        if (firstOfSession) openMenu(Tab.CONTROLS)
    }

    override fun onResume() {
        super.onResume()
        view.onResume()
        if (away && !testing) {
            away = false
            view.send { clearKeys() }
            if (!menu.isOpen) {
                menuSettingsBefore = settings
                view.send { paused = true }
            }
            menu.openAtResume()
            renderMenu()
        }
        handler.post(tick)
    }

    override fun onPause() {
        away = true
        handler.removeCallbacks(tick)
        releaseScreen()
        view.onPause()
        super.onPause()
    }

    private fun now() = SystemClock.elapsedRealtime() / 1000.0

    // --- keys ------------------------------------------------------------------------------

    private fun state(): InputState {
        val snap = view.snapshot
        val phase = snap?.phase ?: RoundPhase.GROW
        return InputState(
            menuOpen = menu.isOpen,
            phase = phase,
            winScreen = winShown,
            mazeInProgress = phase == RoundPhase.PLAY && snap?.timerRunning == true,
        )
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        val commands = input.down(remoteKey(keyCode), event.repeatCount, state(), now())
            ?: return super.onKeyDown(keyCode, event)
        commands.forEach { run(it) }
        return true
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        val key = remoteKey(keyCode)
        if (key == RemoteKey.BACK) return true // handled on the way down; stops onBackPressed
        val commands = input.up(key) ?: return super.onKeyUp(keyCode, event)
        commands.forEach { run(it) }
        return true
    }

    private fun run(c: Command) {
        when (c) {
            is Command.Press -> view.send { pressArrow(c.d) }
            is Command.Release -> view.send { releaseArrow(c.d) }
            Command.SkipGrowth -> view.send { skipGrowth() }
            Command.OpenMenu -> openMenu(null)
            is Command.Menu -> menuKey(c)
            is Command.Zoom -> changeSettings(settings.copy(zoomSteps = (settings.zoomSteps + c.steps).coerceIn(0, 12)))
            Command.Leave -> finish()
            Command.BackHint -> {
                backHint.visibility = View.VISIBLE
                handler.removeCallbacks(hideBackHint)
                handler.postDelayed(hideBackHint, BACK_HINT_MS)
            }
            is Command.WinPick -> renderWin()
            is Command.WinConfirm -> {
                winDismissed = true
                hideWin()
                if (c.choice == 0) view.send { newRound() } else view.send { replay() }
            }
        }
    }

    // --- menu ------------------------------------------------------------------------------

    private fun openMenu(first: Tab?) {
        menuSettingsBefore = settings
        menu.open(now(), first)
        view.send { paused = true }
        if (screenHeld) releaseScreen()
        renderMenu()
    }

    private fun menuKey(c: Command.Menu) {
        when (val effect = menu.key(c.key, settings, now(), c.repeatCount)) {
            MenuEffect.None -> renderMenu()
            is MenuEffect.Changed -> {
                changeSettings(effect.settings)
                renderMenu()
            }
            MenuEffect.Closed -> closeMenu(null)
            is MenuEffect.Run ->
                if (effect.action == MenuAction.TEST_REMOTE) startTest() else closeMenu(effect.action)
        }
    }

    /** The game stays paused behind the test; the menu comes back on Movement afterwards. */
    private fun startTest() {
        testing = true
        menuPanel.visibility = View.GONE
        startActivityForResult(Intent(this, RemoteTestActivity::class.java), REQUEST_TEST)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_TEST) return
        testing = false
        away = false
        remote = GameStore.loadRemote(this) ?: remote
        val r = remote
        view.send { setRemote(r) }
        menu.open(now()) // closed moments ago, so it reopens where it was: Movement
        renderMenu()
    }

    private fun closeMenu(action: MenuAction?) {
        menuPanel.visibility = View.GONE
        val before = menuSettingsBefore
        menuSettingsBefore = null
        val newMaze = action == MenuAction.NEW_MAZE || (before != null && needsNewMaze(before, settings))
        view.send {
            paused = false
            if (newMaze) newRound()
            when (action) {
                MenuAction.HINT -> hint()
                MenuAction.AUTO_SOLVE -> toggleAuto()
                MenuAction.FLASH -> flash()
                MenuAction.REPLAY -> replay()
                MenuAction.RESUME, MenuAction.NEW_MAZE, MenuAction.TEST_REMOTE, null -> {}
            }
        }
        if (newMaze || action == MenuAction.REPLAY) {
            winDismissed = true
            hideWin()
        }
    }

    private fun changeSettings(next: GameSettings) {
        settings = next
        GameStore.save(this, next)
        view.send { applySettings(next) }
    }

    private fun renderMenu() {
        menuPanel.removeAllViews()
        if (!menu.isOpen) {
            menuPanel.visibility = View.GONE
            return
        }
        menuPanel.visibility = View.VISIBLE
        val tabs = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        for (t in Tab.entries) {
            val current = t == menu.tab
            tabs.addView(text(t.title, 18f, if (current) ACCENT else DIM_TEXT).apply {
                setPadding(dp(12), dp(6), dp(12), dp(6))
                if (current) background = rounded(FOCUSED)
            })
        }
        menuPanel.addView(tabs)
        menuPanel.addView(View(this), LinearLayout.LayoutParams(MATCH, dp(12)))
        if (menu.tab == Tab.PLAY) {
            val snap = view.snapshot
            if (snap != null && snap.phase != RoundPhase.GROW) {
                menuPanel.addView(text("Explored ${snap.explored} \u00b7 ${formatTime(snap.elapsed)}", 16f, DIM_TEXT).apply {
                    setPadding(dp(12), 0, dp(12), dp(8))
                })
            }
        }
        val selected = menu.selectedRow(settings)
        for (row in rows(menu.tab, settings)) {
            val isSelected = row.selectable && row == selected
            menuPanel.addView(rowView(row, isSelected))
        }
    }

    private fun rowView(row: Row, selected: Boolean): View {
        if (row is Row.Text) {
            val note = menu.tab != Tab.CONTROLS
            return text(row.text, if (note) 15f else 17f, if (note) DIM_TEXT else TEXT).apply {
                setPadding(dp(12), if (note) dp(12) else dp(4), dp(12), dp(4))
            }
        }
        val line = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(8))
            if (selected) background = rounded(FOCUSED)
        }
        when (row) {
            is Row.Action -> line.addView(text(
                if (row.action == MenuAction.TEST_REMOTE) "Test remote (${remote.arrowLagMs} ms)" else row.action.label,
                19f, TEXT,
            ))
            is Row.Setting -> {
                val f = row.field
                line.addView(text(f.label, 19f, TEXT), LinearLayout.LayoutParams(0, WRAP, 1f))
                val value = f.format(f.get(settings))
                val editing = selected && menu.editing
                line.addView(text(if (editing) "<  $value  >" else value, 19f, if (editing || f.kind == Kind.TOGGLE) ACCENT else DIM_TEXT).apply {
                    typeface = Typeface.MONOSPACE
                })
            }
            else -> {}
        }
        return line
    }

    // --- win panel and readout ----------------------------------------------------------------

    private fun refresh() {
        val snap = view.snapshot ?: return
        readout.text = if (snap.phase == RoundPhase.GROW) "" else "Explored ${snap.explored} \u00b7 ${formatTime(snap.elapsed)}"
        if (!snap.winScreen) winDismissed = false
        if (snap.winScreen && !winShown && !winDismissed && !menu.isOpen) {
            winShown = true
            input.resetWin()
            renderWin()
        } else if (!snap.winScreen && winShown) {
            hideWin()
        }
        val hold = snap.dotMoving && !menu.isOpen
        if (hold && !screenHeld) {
            window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            screenHeld = true
        } else if (!hold && screenHeld) {
            releaseScreen()
        }
    }

    private fun releaseScreen() {
        window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        screenHeld = false
    }

    private fun renderWin() {
        val snap = view.snapshot ?: return
        winPanel.removeAllViews()
        winPanel.visibility = View.VISIBLE
        winPanel.addView(text("Solved!", 30f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
        }, LinearLayout.LayoutParams(MATCH, WRAP))
        if (snap.assisted) {
            winPanel.addView(text("Assisted", 16f, WARN).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(MATCH, WRAP))
        }
        val lines = mutableListOf(
            "Cells explored" to snap.explored.toString(),
            "Shortest route" to snap.shortest.toString(),
            "Efficiency" to "${snap.efficiency}%",
            "Time" to formatTime(snap.elapsed),
            "Hints used" to snap.hints.toString(),
        )
        if (snap.assisted) lines.add("Auto-solved cells" to snap.autoExplored.toString())
        for ((label, value) in lines) {
            winPanel.addView(LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(dp(12), dp(6), dp(12), dp(6))
                addView(text(label, 18f, DIM_TEXT), LinearLayout.LayoutParams(0, WRAP, 1f))
                addView(text(value, 18f, TEXT))
            })
        }
        val buttons = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
            setPadding(0, dp(16), 0, 0)
        }
        listOf("New maze", "Replay").forEachIndexed { i, label ->
            val chosen = i == input.winChoice
            buttons.addView(text(label, 20f, if (chosen) ACCENT else TEXT).apply {
                setPadding(dp(20), dp(10), dp(20), dp(10))
                if (chosen) background = rounded(FOCUSED)
            })
        }
        winPanel.addView(buttons, LinearLayout.LayoutParams(MATCH, WRAP))
    }

    private fun hideWin() {
        winShown = false
        winPanel.visibility = View.GONE
    }

    // --- views -----------------------------------------------------------------------------

    private fun panel() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(24), dp(20), dp(24), dp(20))
        background = rounded(PANEL)
    }

    private fun rounded(color: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(10).toFloat()
    }

    private fun text(value: String, sizeSp: Float, color: Int) = TextView(this).apply {
        text = value
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
        setTextColor(color)
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private companion object {
        const val REQUEST_TEST = 1
        const val WRAP = LinearLayout.LayoutParams.WRAP_CONTENT
        const val MATCH = LinearLayout.LayoutParams.MATCH_PARENT
    }
}
