// Labyrinth Mobile's game screen. The window never rotates: the maze is fixed to the glass
// between two toolbar strips at the screen's short ends (BoardLayout), and only the toolbar
// and the panels turn to face the player (RotatedFrame), following the orientation sensor.
// Swipes on the maze and keys from keyboards and controllers become commands for the game
// on GameView's render thread. A 100 ms tick reads the render thread's snapshot to update the
// toolbar and the win panel and to hold the screen on only while the dot moves.
package com.bydesigninteractive.labyrinth.mobile

import android.app.Activity
import android.content.res.Configuration
import android.graphics.Color
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.OrientationEventListener
import android.view.ScaleGestureDetector
import android.view.View
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bydesigninteractive.labyrinth.BACKGROUND
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.TEXT
import com.bydesigninteractive.labyrinth.game.Command
import com.bydesigninteractive.labyrinth.game.GameInput
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.InputState
import com.bydesigninteractive.labyrinth.game.MenuAction
import com.bydesigninteractive.labyrinth.game.PLAY_ACTIONS
import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.game.RoundPhase
import com.bydesigninteractive.labyrinth.game.ZOOM_STEP
import com.bydesigninteractive.labyrinth.game.phoneGrid
import com.bydesigninteractive.labyrinth.game.plausiblePpi
import com.bydesigninteractive.labyrinth.play.GameRenderer
import com.bydesigninteractive.labyrinth.play.GameStore
import com.bydesigninteractive.labyrinth.play.GameView
import com.bydesigninteractive.labyrinth.play.MazeSizer
import com.bydesigninteractive.labyrinth.play.formatTime
import com.bydesigninteractive.labyrinth.touch.Hold
import com.bydesigninteractive.labyrinth.touch.SWIPE_DP
import com.bydesigninteractive.labyrinth.touch.Strip
import com.bydesigninteractive.labyrinth.touch.SwipeTracker
import com.bydesigninteractive.labyrinth.touch.rotateKey
import com.bydesigninteractive.labyrinth.touch.toolbarStrip
import com.bydesigninteractive.labyrinth.touch.turnsFor

private const val TICK_MS = 100L
private const val BACK_HINT_MS = 2000L
private const val STRIP_DP = 56
private const val MAX_ZOOM_STEPS = 12
private val PANEL = Color.argb(240, 16, 18, 22)
private val SCRIM = Color.argb(120, 0, 0, 0)
private val WARN = Color.rgb(235, 170, 60)
private val ARROWS = setOf(RemoteKey.UP, RemoteKey.DOWN, RemoteKey.LEFT, RemoteKey.RIGHT)

class MobileGameActivity : Activity() {
    private lateinit var view: GameView
    private lateinit var settings: GameSettings
    private val input = GameInput()
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var startStrip: RotatedFrame
    private lateinit var endStrip: RotatedFrame
    private lateinit var overlay: RotatedFrame
    private lateinit var toolbar: GameToolbar
    private lateinit var scrim: View
    private lateinit var playPanel: LinearLayout
    private lateinit var winPanel: LinearLayout
    /** Each panel sits in a scroller, so a phone held sideways can reach all of it. */
    private lateinit var playScroll: ScrollView
    private lateinit var winScroll: ScrollView
    private lateinit var backHint: TextView
    private lateinit var swipes: SwipeTracker
    private lateinit var scale: ScaleGestureDetector
    private lateinit var orientation: OrientationEventListener
    /** Clockwise quarter turns from the natural up to the player's up (see touch/Rotation.kt). */
    private var turns = 0
    /** Whether the screen (in its natural orientation) is taller than wide. */
    private var tall = true
    /** Pixels per inch for the render thread's maze sizer. */
    @Volatile private var ppi = 160.0
    private var panelOpen = false
    private var firstPlayButton: View? = null
    private var firstWinButton: View? = null
    private var winShown = false
    /** The win panel was just dismissed; ignore stale win snapshots until one without winScreen arrives. */
    private var winDismissed = false
    private var screenHeld = false
    private var pinching = false
    private var pinchScale = 1f
    /** Arrow keys held down, as the (turned) arrow each pressed: the phone may turn while one is held. */
    private val heldKeys = HashMap<Int, RemoteKey>()

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
        updatePpi()
        view = GameView(this, settings, RemoteProfile(), startPaused = false,
            sizer = MazeSizer { s, w, h, rng -> phoneGrid(s, w, h, ppi, rng) })
        toolbar = GameToolbar(this, onHint = { view.send { hint() } }, onMenu = ::openPanel)
        startStrip = RotatedFrame(this).apply { setBackgroundColor(BACKGROUND) }
        endStrip = RotatedFrame(this).apply { setBackgroundColor(BACKGROUND) }
        val board = BoardLayout(this, dp(STRIP_DP), view, startStrip, endStrip) { isTall ->
            tall = isTall
            placeToolbar()
        }
        overlay = RotatedFrame(this)
        scrim = View(this).apply {
            setBackgroundColor(SCRIM)
            visibility = View.GONE
            setOnClickListener { closePanel(null) }
        }
        playPanel = panel()
        winPanel = panel()
        playScroll = scroller(playPanel)
        winScroll = scroller(winPanel)
        backHint = label("Press Back again to leave", 16f, TEXT).apply {
            setPadding(dp(20), dp(10), dp(20), dp(10))
            background = rounded(PANEL, dp(10).toFloat())
            visibility = View.GONE
        }
        overlay.content.apply {
            addView(scrim, FrameLayout.LayoutParams(MATCH, MATCH))
            addView(playScroll, FrameLayout.LayoutParams(dp(320), WRAP, Gravity.CENTER).apply {
                topMargin = dp(12)
                bottomMargin = dp(12)
            })
            addView(winScroll, FrameLayout.LayoutParams(dp(340), WRAP, Gravity.CENTER).apply {
                topMargin = dp(12)
                bottomMargin = dp(12)
            })
            addView(backHint, FrameLayout.LayoutParams(WRAP, WRAP, Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply {
                bottomMargin = dp(88)
            })
        }
        playScroll.visibility = View.GONE
        winScroll.visibility = View.GONE
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            addView(board, FrameLayout.LayoutParams(MATCH, MATCH))
            addView(this@MobileGameActivity.overlay, FrameLayout.LayoutParams(MATCH, MATCH))
        }
        // The layout keeps clear of a camera cutout; hidden system bars take no space.
        root.setOnApplyWindowInsetsListener { v, insets ->
            val cutout = if (Build.VERSION.SDK_INT >= 28) insets.displayCutout else null
            v.setPadding(cutout?.safeInsetLeft ?: 0, cutout?.safeInsetTop ?: 0, cutout?.safeInsetRight ?: 0, cutout?.safeInsetBottom ?: 0)
            insets
        }
        if (Build.VERSION.SDK_INT >= 28) {
            window.attributes = window.attributes.apply {
                layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            }
        }
        setContentView(root)

        swipes = SwipeTracker(SWIPE_DP * resources.displayMetrics.density)
        scale = ScaleGestureDetector(this, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
            override fun onScaleBegin(detector: ScaleGestureDetector): Boolean {
                pinchScale = 1f
                return true
            }

            override fun onScale(detector: ScaleGestureDetector): Boolean {
                pinchScale *= detector.scaleFactor
                val step = ZOOM_STEP.toFloat()
                val steps = when {
                    pinchScale >= step -> 1
                    pinchScale <= 1f / step -> -1
                    else -> 0
                }
                if (steps != 0) {
                    pinchScale = 1f
                    zoomBy(steps)
                }
                return true
            }
        })
        // A tap followed by a one-finger drag steers; it must not also zoom.
        scale.isQuickScaleEnabled = false
        view.setOnTouchListener { _, e ->
            onBoardTouch(e)
            true
        }
        orientation = object : OrientationEventListener(this) {
            override fun onOrientationChanged(degrees: Int) {
                val next = turnsFor(degrees, turns, Hold.AUTO, tall)
                if (next != turns) setTurns(next)
            }
        }
    }

    override fun onResume() {
        super.onResume()
        hideSystemBars()
        view.onResume()
        view.send { clearKeys() }
        if (orientation.canDetectOrientation()) orientation.enable()
        handler.post(tick)
    }

    override fun onPause() {
        handler.removeCallbacks(tick)
        orientation.disable()
        heldKeys.clear()
        releaseScreen()
        view.onPause()
        super.onPause()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) hideSystemBars()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        updatePpi() // a foldable's other screen can have a different density
    }

    private fun updatePpi() {
        val m = resources.displayMetrics
        ppi = plausiblePpi(m.xdpi, m.ydpi, m.densityDpi)
    }

    private fun hideSystemBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            // Still needed below API 35, where edge-to-edge is not the default.
            @Suppress("DEPRECATION")
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.let {
                it.hide(WindowInsets.Type.systemBars())
                it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            }
        } else {
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or View.SYSTEM_UI_FLAG_LAYOUT_STABLE or
                View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
        }
    }

    private fun now() = SystemClock.elapsedRealtime() / 1000.0

    // --- turning -----------------------------------------------------------------------------

    private fun setTurns(next: Int) {
        turns = next
        overlay.turns = next
        placeToolbar()
    }

    /** Puts the toolbar in the strip at the player's top (or left), turned to read upright. */
    private fun placeToolbar() {
        val target = if (toolbarStrip(turns, tall) == Strip.START) startStrip else endStrip
        startStrip.turns = turns
        endStrip.turns = turns
        toolbar.setVertical(tall == (turns % 2 == 1))
        if (toolbar.parent !== target.content) {
            (toolbar.parent as? FrameLayout)?.removeView(toolbar)
            target.content.addView(toolbar, FrameLayout.LayoutParams(MATCH, MATCH))
        }
    }

    // --- touch -------------------------------------------------------------------------------

    private fun onBoardTouch(e: MotionEvent) {
        scale.onTouchEvent(e)
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                pinching = false
                swipes.down(e.x, e.y)
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                pinching = true // two fingers zoom; they never steer
                swipes.cancel()
            }
            MotionEvent.ACTION_MOVE -> if (!pinching) swipes.move(e.x, e.y)?.let { d -> view.send { swipe(d) } }
            MotionEvent.ACTION_UP -> {
                val steered = swipes.up()
                if (!steered && !pinching && view.snapshot?.phase == RoundPhase.GROW) view.send { skipGrowth() }
            }
            MotionEvent.ACTION_CANCEL -> swipes.cancel()
        }
    }

    private fun zoomBy(steps: Int) {
        changeSettings(settings.copy(zoomSteps = (settings.zoomSteps + steps).coerceIn(0, MAX_ZOOM_STEPS)))
    }

    private fun changeSettings(next: GameSettings) {
        settings = next
        GameStore.save(this, next)
        view.send { applySettings(next) }
    }

    // --- keys --------------------------------------------------------------------------------

    private fun state(): InputState {
        val snap = view.snapshot
        val phase = snap?.phase ?: RoundPhase.GROW
        return InputState(
            menuOpen = false,
            phase = phase,
            winScreen = false,
            mazeInProgress = phase == RoundPhase.PLAY && snap?.timerRunning == true,
        )
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        val key = phoneKey(keyCode)
        if (key == RemoteKey.BACK) {
            if (event.repeatCount == 0) {
                when {
                    panelOpen -> closePanel(null)
                    winShown -> finish()
                    else -> input.down(key, 0, state(), now())?.forEach(::run)
                }
            }
            return true
        }
        if (panelOpen || winShown) {
            // The panels' buttons take arrows through Android's focus navigation.
            if (key == RemoteKey.OK) {
                if (event.repeatCount == 0) pressFocused()
                return true
            }
            return super.onKeyDown(keyCode, event)
        }
        if (key == RemoteKey.OTHER) return super.onKeyDown(keyCode, event)
        val turned = rotateKey(key, turns)
        val commands = input.down(turned, event.repeatCount, state(), now()) ?: return super.onKeyDown(keyCode, event)
        if (event.repeatCount == 0 && turned in ARROWS) heldKeys[keyCode] = turned
        commands.forEach(::run)
        return true
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (phoneKey(keyCode) == RemoteKey.BACK) return true // handled on the way down
        val turned = heldKeys.remove(keyCode) ?: return super.onKeyUp(keyCode, event)
        input.up(turned)?.forEach(::run)
        return true
    }

    /** OK on a panel: clicks the focused button, or focuses the first one. */
    private fun pressFocused() {
        val focused = currentFocus
        if (focused != null && focused.isFocusable && focused !== view) {
            focused.performClick()
        } else {
            (if (panelOpen) firstPlayButton else firstWinButton)?.requestFocus()
        }
    }

    private fun run(c: Command) {
        when (c) {
            is Command.Press -> view.send { pressArrow(c.d) }
            is Command.Release -> view.send { releaseArrow(c.d) }
            Command.SkipGrowth -> view.send { skipGrowth() }
            Command.OpenMenu -> openPanel()
            is Command.Zoom -> zoomBy(c.steps)
            Command.Leave -> finish()
            Command.BackHint -> {
                backHint.visibility = View.VISIBLE
                handler.removeCallbacks(hideBackHint)
                handler.postDelayed(hideBackHint, BACK_HINT_MS)
            }
            // The panels take keys through focus navigation, not GameInput's menu and win keys.
            is Command.Menu, is Command.WinPick, is Command.WinConfirm -> {}
        }
    }

    // --- the Play panel ----------------------------------------------------------------------

    private fun openPanel() {
        if (panelOpen) return
        panelOpen = true
        heldKeys.clear()
        view.send {
            paused = true
            clearKeys()
        }
        if (screenHeld) releaseScreen()
        if (winShown) hideWin()
        renderPlayPanel()
        scrim.visibility = View.VISIBLE
        playScroll.visibility = View.VISIBLE
    }

    private fun closePanel(action: MenuAction?) {
        if (!panelOpen) return
        panelOpen = false
        playScroll.visibility = View.GONE
        scrim.visibility = View.GONE
        val newMaze = action == MenuAction.NEW_MAZE
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

    private fun renderPlayPanel() {
        playPanel.removeAllViews()
        val snap = view.snapshot
        if (snap != null && snap.phase != RoundPhase.GROW) {
            playPanel.addView(label("Explored ${snap.explored} · ${formatTime(snap.elapsed)}", 15f, DIM_TEXT).apply {
                gravity = Gravity.CENTER
                setPadding(0, 0, 0, dp(8))
            }, LinearLayout.LayoutParams(MATCH, WRAP))
        }
        firstPlayButton = null
        for (action in PLAY_ACTIONS) {
            val button = panelButton(action.label) { closePanel(action) }
            if (firstPlayButton == null) firstPlayButton = button
            playPanel.addView(button, LinearLayout.LayoutParams(MATCH, WRAP).apply { topMargin = dp(8) })
        }
    }

    // --- win panel and toolbar ---------------------------------------------------------------

    private fun refresh() {
        val snap = view.snapshot ?: return
        toolbar.show(if (snap.phase == RoundPhase.GROW) null else snap.explored, snap.elapsed)
        if (!snap.winScreen) winDismissed = false
        if (snap.winScreen && !winShown && !winDismissed && !panelOpen) {
            winShown = true
            heldKeys.clear()
            renderWin()
        } else if (!snap.winScreen && winShown) {
            hideWin()
        }
        val hold = snap.dotMoving && !panelOpen
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
        winScroll.visibility = View.VISIBLE
        winPanel.addView(label("Solved!", 28f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
        }, LinearLayout.LayoutParams(MATCH, WRAP))
        if (snap.assisted) {
            winPanel.addView(label("Assisted", 15f, WARN).apply { gravity = Gravity.CENTER }, LinearLayout.LayoutParams(MATCH, WRAP))
        }
        val lines = mutableListOf(
            "Cells explored" to snap.explored.toString(),
            "Shortest route" to snap.shortest.toString(),
            "Efficiency" to "${snap.efficiency}%",
            "Time" to formatTime(snap.elapsed),
            "Hints used" to snap.hints.toString(),
        )
        if (snap.assisted) lines.add("Auto-solved cells" to snap.autoExplored.toString())
        for ((name, value) in lines) {
            winPanel.addView(LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                setPadding(dp(4), dp(5), dp(4), dp(5))
                addView(label(name, 16f, DIM_TEXT), LinearLayout.LayoutParams(0, WRAP, 1f))
                addView(label(value, 16f, TEXT))
            })
        }
        val buttons = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(16), 0, 0)
        }
        val newMaze = panelButton("New maze") { dismissWin { newRound() } }
        val replay = panelButton("Replay") { dismissWin { replay() } }
        buttons.addView(newMaze, LinearLayout.LayoutParams(0, WRAP, 1f).apply { marginEnd = dp(6) })
        buttons.addView(replay, LinearLayout.LayoutParams(0, WRAP, 1f).apply { marginStart = dp(6) })
        firstWinButton = newMaze
        winPanel.addView(buttons, LinearLayout.LayoutParams(MATCH, WRAP))
    }

    private fun dismissWin(then: GameRenderer.() -> Unit) {
        winDismissed = true
        hideWin()
        view.send(then)
    }

    private fun hideWin() {
        winShown = false
        winScroll.visibility = View.GONE
    }

    private fun panel() = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(20), dp(18), dp(20), dp(18))
        background = rounded(PANEL, dp(12).toFloat())
        // Takes its own taps: the padding and header must not fall through to the scrim or the maze.
        isClickable = true
    }

    private fun scroller(panel: LinearLayout) = ScrollView(this).apply {
        isFillViewport = false
        isVerticalScrollBarEnabled = false
        addView(panel, FrameLayout.LayoutParams(MATCH, WRAP))
    }

    private companion object {
        const val WRAP = FrameLayout.LayoutParams.WRAP_CONTENT
        const val MATCH = FrameLayout.LayoutParams.MATCH_PARENT
    }
}
