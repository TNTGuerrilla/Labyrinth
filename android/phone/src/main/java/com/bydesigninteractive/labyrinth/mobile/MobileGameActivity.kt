// Labyrinth Mobile's game screen. The window never rotates: the maze is fixed to the glass
// between two toolbar strips at the screen's short ends (BoardLayout), and only the toolbar
// and the panels turn to face the player (RotatedFrame), following the orientation sensor.
// Swipes on the maze and keys from keyboards and controllers become commands for the game
// on GameView's render thread. A 100 ms tick reads the render thread's snapshot to update the
// toolbar and the win panel and to hold the screen on only while the dot moves.
package com.bydesigninteractive.labyrinth.mobile

import android.app.Activity
import android.content.Intent
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
import android.view.ViewConfiguration
import android.view.WindowInsets
import android.view.WindowInsetsController
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import com.bydesigninteractive.labyrinth.BACKGROUND
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.TEXT
import com.bydesigninteractive.labyrinth.styledNotes
import com.bydesigninteractive.labyrinth.update.RELEASES_TEXT
import com.bydesigninteractive.labyrinth.update.Release
import com.bydesigninteractive.labyrinth.update.UpdateStore
import com.bydesigninteractive.labyrinth.update.Updates
import com.bydesigninteractive.labyrinth.update.WhatsNew
import com.bydesigninteractive.labyrinth.update.notesBetween
import com.bydesigninteractive.labyrinth.update.withArrivedNotes
import com.bydesigninteractive.labyrinth.game.Command
import com.bydesigninteractive.labyrinth.game.GameInput
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.InputState
import com.bydesigninteractive.labyrinth.game.MenuAction
import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.game.RoundPhase
import com.bydesigninteractive.labyrinth.game.ZOOM_STEP
import com.bydesigninteractive.labyrinth.game.needsNewMaze
import com.bydesigninteractive.labyrinth.game.phoneGrid
import com.bydesigninteractive.labyrinth.game.plausiblePpi
import com.bydesigninteractive.labyrinth.play.GameRenderer
import com.bydesigninteractive.labyrinth.play.GameStore
import com.bydesigninteractive.labyrinth.play.GameView
import com.bydesigninteractive.labyrinth.play.MazeSizer
import com.bydesigninteractive.labyrinth.play.RemoteTestActivity
import com.bydesigninteractive.labyrinth.play.TestDevice
import com.bydesigninteractive.labyrinth.play.formatTime
import com.bydesigninteractive.labyrinth.touch.SWIPE_DP
import com.bydesigninteractive.labyrinth.touch.Strip
import com.bydesigninteractive.labyrinth.touch.SwipeTracker
import com.bydesigninteractive.labyrinth.touch.rotateKey
import com.bydesigninteractive.labyrinth.touch.toMaze
import com.bydesigninteractive.labyrinth.touch.toolbarStrip
import com.bydesigninteractive.labyrinth.touch.turnsFor
import kotlin.math.hypot

private const val TICK_MS = 100L
private const val BACK_HINT_MS = 2000L
private const val STRIP_DP = 56
private const val MAX_ZOOM_STEPS = 12
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
    private lateinit var updates: UpdateFlow
    private lateinit var scrim: View
    private lateinit var menu: MenuPanel
    private lateinit var phone: PhoneSettings
    private lateinit var appVersion: String
    /** When the menu last closed, for reopening on the same tab within a minute. */
    private var menuClosedAt: Double? = null
    /** The game settings when the menu opened: closing it starts a new maze if the size changed. */
    private var menuSettingsBefore: GameSettings? = null
    private lateinit var winPanel: LinearLayout
    /** The win panel sits in a scroller, so a phone held sideways can reach all of it. */
    private lateinit var winScroll: CappedScroll
    private lateinit var cardPanel: LinearLayout
    private lateinit var cardScroll: CappedScroll
    private var cardOpen = false
    private var cardButton: View? = null
    private lateinit var backHint: TextView
    private lateinit var swipes: SwipeTracker
    private lateinit var joystick: JoystickView
    /** The maze direction the joystick is holding, turned when it was pressed. */
    private var stickDir: Int? = null
    private var downX = 0f
    private var downY = 0f
    /** The finger moved beyond a tap. */
    private var moved = false
    private var tapSlop = 0
    /** The orientation sensor's last reading, so switching to Auto follows it at once. */
    private var lastDegrees = -1
    private var remote = RemoteProfile()
    private lateinit var scale: ScaleGestureDetector
    private lateinit var orientation: OrientationEventListener
    /** Clockwise quarter turns from the natural up to the player's up (see touch/Rotation.kt). */
    private var turns = 0
    /** Whether the screen (in its natural orientation) is taller than wide. */
    private var tall = true
    /** Pixels per inch for the render thread's maze sizer. */
    @Volatile private var ppi = 160.0
    private var menuOpen = false
    /** Set once a controller has been used; the menu then offers the controller test. */
    private var controllerUsed = false
    private var firstWinButton: View? = null
    private var winShown = false
    /** The win panel was just dismissed; ignore stale win snapshots until one without winScreen arrives. */
    private var winDismissed = false
    private var screenHeld = false
    private var pinching = false
    private var pinchScale = 1f
    /** Arrow keys held down, as the (turned) arrow each pressed: the phone may turn while one is held. */
    private val heldKeys = HashMap<Int, RemoteKey>()

    private val menuHost = object : MenuPanel.Host {
        override val game: GameSettings get() = settings
        override val phone: PhoneSettings get() = this@MobileGameActivity.phone
        override val version: String get() = appVersion
        override val controllerUsed: Boolean get() = this@MobileGameActivity.controllerUsed
        override val canUpdate: Boolean get() = updates.canUpdate
        override fun updateStatus(): String = updates.status
        override val checksOn: Boolean get() = updates.checksOn
        override fun toggleChecks() = updates.toggleChecks()

        override fun readout(): String? {
            val snap = view.snapshot ?: return null
            return if (snap.phase == RoundPhase.GROW) null else "Explored ${snap.explored} \u00b7 ${formatTime(snap.elapsed)}"
        }

        override fun changeGame(next: GameSettings) = changeSettings(next)
        override fun changePhone(next: PhoneSettings) = changePhoneSettings(next)
        override fun runAction(action: MenuAction) = closeMenu(action)
        override fun openLink(link: MenuLink) {
            when (link) {
                MenuLink.HOW_TO_PLAY -> {
                    closeMenu(null)
                    showHowToPlay()
                }
                MenuLink.UPDATE -> updates.startUpdate()
                MenuLink.DISMISS -> updates.dismiss()
                MenuLink.CHECK_NOW -> updates.checkNow()
                MenuLink.WHATS_NEW -> {
                    closeMenu(null)
                    val news = UpdateStore.runningWhatsNew(this@MobileGameActivity, updates.current)
                    showWhatsNew(news)
                    // Read first: marking a pending What's new seen drops its notes. Now shown, it counts as seen.
                    UpdateStore.markWhatsNewSeen(this@MobileGameActivity, updates.current)
                }
                MenuLink.CONTROLLER_TEST -> {
                    closeMenu(null)
                    view.send { paused = true }
                    startActivityForResult(
                        Intent(this@MobileGameActivity, RemoteTestActivity::class.java)
                            .putExtra(RemoteTestActivity.EXTRA_DEVICE, TestDevice.CONTROLLER.name),
                        REQUEST_TEST,
                    )
                }
            }
        }

        override fun close() = closeMenu(null)
    }

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
        phone = PhoneStore.load(this)
        appVersion = packageManager.getPackageInfo(packageName, 0).versionName ?: ""
        updatePpi()
        updates = UpdateFlow(this) { onUpdateChange() }
        remote = GameStore.loadRemote(this) ?: RemoteProfile()
        controllerUsed = PhoneStore.controllerUsed(this)
        view = GameView(this, settings, remote, startPaused = savedInstanceState == null && !PhoneStore.howToPlaySeen(this),
            sizer = MazeSizer { s, w, h, rng -> phoneGrid(s, w, h, ppi, rng) })
        view.send { setShowTrace(phone.showTrace) }
        toolbar = GameToolbar(this, onHint = { view.send { hint() } }, onMenu = ::openMenu)
        startStrip = RotatedFrame(this).apply { setBackgroundColor(BACKGROUND) }
        endStrip = RotatedFrame(this).apply { setBackgroundColor(BACKGROUND) }
        val board = BoardLayout(this, dp(STRIP_DP), view, startStrip, endStrip) { isTall ->
            tall = isTall
            setTurns(turnsFor(-1, turns, phone.hold, tall))
        }
        overlay = RotatedFrame(this)
        scrim = View(this).apply {
            setBackgroundColor(SCRIM)
            visibility = View.GONE
            setOnClickListener { if (cardOpen) closeCard() else closeMenu(null) }
        }
        menu = MenuPanel(this, menuHost)
        winPanel = panel()
        winScroll = scroller(winPanel, 340)
        cardPanel = panel()
        cardScroll = scroller(cardPanel, 360)
        backHint = label("Press Back again to leave", 16f, TEXT).apply {
            setPadding(dp(20), dp(10), dp(20), dp(10))
            background = rounded(PANEL, dp(10).toFloat())
            visibility = View.GONE
        }
        joystick = JoystickView(this) { seen ->
            if (menuOpen || cardOpen) return@JoystickView
            stickDir?.let { d -> view.send { releaseTouch(d) } }
            stickDir = seen?.let { toMaze(it, turns) }
            stickDir?.let { d -> view.send { holdTouch(d) } }
        }
        overlay.content.apply {
            addView(joystick, 0, FrameLayout.LayoutParams(dp(150), dp(150)))
            addView(scrim, FrameLayout.LayoutParams(MATCH, MATCH))
            addView(menu, FrameLayout.LayoutParams(MATCH, WRAP, Gravity.CENTER).apply { setMargins(dp(12), dp(12), dp(12), dp(12)) })
            addView(winScroll, FrameLayout.LayoutParams(MATCH, WRAP, Gravity.CENTER).apply { setMargins(dp(12), dp(12), dp(12), dp(12)) })
            addView(cardScroll, FrameLayout.LayoutParams(MATCH, WRAP, Gravity.CENTER).apply { setMargins(dp(12), dp(12), dp(12), dp(12)) })
            addView(backHint, FrameLayout.LayoutParams(WRAP, WRAP, Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply {
                bottomMargin = dp(88)
            })
        }
        placeJoystick()
        menu.visibility = View.GONE
        winScroll.visibility = View.GONE
        cardScroll.visibility = View.GONE
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            addView(board, FrameLayout.LayoutParams(MATCH, MATCH))
            addView(this@MobileGameActivity.overlay, FrameLayout.LayoutParams(MATCH, MATCH))
        }
        // The layout keeps clear of a camera cutout, and of the system bars when they are shown.
        root.setOnApplyWindowInsetsListener { v, insets ->
            val (l, t, r, b) = safeInsets(insets)
            v.setPadding(l, t, r, b)
            insets
        }
        if (Build.VERSION.SDK_INT >= 28) {
            window.attributes = window.attributes.apply {
                layoutInDisplayCutoutMode = WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES
            }
        }
        setContentView(root)

        swipes = SwipeTracker(SWIPE_DP * resources.displayMetrics.density)
        tapSlop = ViewConfiguration.get(this).scaledTouchSlop
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
                lastDegrees = degrees
                val next = turnsFor(degrees, turns, phone.hold, tall)
                if (next != turns) setTurns(next)
            }
        }
        // An install report opens the About menu, which must not sit over a launch card (closing
        // the menu would leave the maze running behind the card), so it takes the launch card's place.
        val reported = handleInstallReport(intent)
        if (savedInstanceState == null) {
            val news = UpdateStore.startWhatsNew(this, updates.current) // once per fresh launch
            val offer = updates.pending()
            val first = if (reported) null else launchCard(!PhoneStore.howToPlaySeen(this), news != null, offer != null)
            when (first) {
                LaunchCard.HOW_TO_PLAY -> showHowToPlay()
                LaunchCard.WHATS_NEW -> {
                    showWhatsNew(news!!)
                    UpdateStore.markWhatsNewSeen(this, updates.current) // shown once: it counts as seen
                }
                LaunchCard.UPDATE -> showUpdateCard(offer!!)
                null -> {}
            }
        }
    }

    override fun onResume() {
        super.onResume()
        updates.onResume()
        applySystemBars()
        view.onResume()
        view.send { clearKeys() }
        if (orientation.canDetectOrientation()) orientation.enable()
        handler.post(tick)
    }

    override fun onPause() {
        handler.removeCallbacks(tick)
        orientation.disable()
        heldKeys.clear()
        letGoOfStick()
        releaseScreen()
        view.onPause()
        super.onPause()
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) applySystemBars()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        updatePpi() // a foldable's other screen can have a different density
    }

    private fun updatePpi() {
        val m = resources.displayMetrics
        ppi = plausiblePpi(m.xdpi, m.ydpi, m.densityDpi)
    }

    /** Hides the status and navigation bars, or shows them, as the Look setting says. */
    private fun applySystemBars() {
        if (Build.VERSION.SDK_INT >= 30) {
            // Still needed below API 35, where edge-to-edge is not the default.
            @Suppress("DEPRECATION")
            window.setDecorFitsSystemWindows(false)
            window.insetsController?.let {
                if (phone.hideBars) {
                    it.hide(WindowInsets.Type.systemBars())
                    it.systemBarsBehavior = WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
                } else {
                    it.show(WindowInsets.Type.systemBars())
                }
            }
        } else {
            val layout = View.SYSTEM_UI_FLAG_LAYOUT_STABLE or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN or
                View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            val hide = View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            @Suppress("DEPRECATION")
            window.decorView.systemUiVisibility = if (phone.hideBars) layout or hide else layout
        }
        window.decorView.requestApplyInsets()
    }

    /** Left, top, right, bottom to keep clear: a camera cutout, and the system bars while they show. */
    private fun safeInsets(insets: WindowInsets): IntArray {
        if (Build.VERSION.SDK_INT >= 30) {
            val types = WindowInsets.Type.displayCutout() or (if (phone.hideBars) 0 else WindowInsets.Type.systemBars())
            val i = insets.getInsets(types)
            return intArrayOf(i.left, i.top, i.right, i.bottom)
        }
        val cutout = if (Build.VERSION.SDK_INT >= 28) insets.displayCutout else null
        @Suppress("DEPRECATION")
        val bars = if (phone.hideBars) intArrayOf(0, 0, 0, 0) else intArrayOf(
            insets.systemWindowInsetLeft, insets.systemWindowInsetTop, insets.systemWindowInsetRight, insets.systemWindowInsetBottom,
        )
        return intArrayOf(
            maxOf(bars[0], cutout?.safeInsetLeft ?: 0),
            maxOf(bars[1], cutout?.safeInsetTop ?: 0),
            maxOf(bars[2], cutout?.safeInsetRight ?: 0),
            maxOf(bars[3], cutout?.safeInsetBottom ?: 0),
        )
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

    /** Shows the joystick for the Joystick scheme, in the player's lower corner on the chosen hand. */
    private fun placeJoystick() {
        val params = joystick.layoutParams as FrameLayout.LayoutParams
        params.gravity = Gravity.BOTTOM or (if (phone.hand == Hand.LEFT) Gravity.START else Gravity.END)
        params.setMargins(dp(24), dp(24), dp(24), dp(24))
        joystick.layoutParams = params
        joystick.visibility = if (phone.touch == TouchScheme.JOYSTICK) View.VISIBLE else View.GONE
        letGoOfStick()
    }

    /** The joystick's hold ends when a panel opens or the app goes away. */
    private fun letGoOfStick() {
        stickDir?.let { d -> view.send { releaseTouch(d) } }
        stickDir = null
        joystick.reset()
    }

    /** The touch scheme the current gesture started with; a setting changed mid-gesture waits for the next. */
    private var gestureScheme = TouchScheme.TAP

    private fun endDrag() {
        if (gestureScheme == TouchScheme.DRAG) view.send { dragEnd() }
    }

    private fun onBoardTouch(e: MotionEvent) {
        scale.onTouchEvent(e)
        if (e.actionMasked == MotionEvent.ACTION_DOWN) gestureScheme = phone.touch
        val scheme = gestureScheme
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                pinching = false
                moved = false
                downX = e.x
                downY = e.y
                when (scheme) {
                    TouchScheme.SWIPE -> swipes.down(e.x, e.y)
                    TouchScheme.DRAG -> {
                        val x = e.x
                        val y = e.y
                        view.send { dragStart(x, y) }
                    }
                    TouchScheme.JOYSTICK, TouchScheme.TAP -> {}
                }
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                pinching = true // two fingers zoom; they never steer
                swipes.cancel()
                endDrag()
            }
            MotionEvent.ACTION_MOVE -> if (!pinching) {
                if (hypot(e.x - downX, e.y - downY) > tapSlop) moved = true
                when (scheme) {
                    TouchScheme.SWIPE -> swipes.move(e.x, e.y)?.let { d -> view.send { swipe(d) } }
                    TouchScheme.DRAG -> traceAt(e.x, e.y)
                    TouchScheme.JOYSTICK, TouchScheme.TAP -> {}
                }
            }
            MotionEvent.ACTION_UP -> {
                val steered = scheme == TouchScheme.SWIPE && swipes.up()
                endDrag()
                if (!pinching && !moved && !steered) {
                    val x = e.x
                    val y = e.y
                    if (view.snapshot?.phase == RoundPhase.GROW) {
                        view.send { skipGrowth() }
                    } else if (scheme == TouchScheme.TAP) {
                        view.send { tapAt(x, y) }
                    }
                }
            }
            MotionEvent.ACTION_CANCEL -> {
                swipes.cancel()
                endDrag()
            }
        }
    }

    private fun traceAt(x: Float, y: Float) = view.send { dragAt(x, y) }

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
        if (!controllerUsed && (key in ARROWS || key == RemoteKey.OK || key == RemoteKey.VOLUME_UP || key == RemoteKey.VOLUME_DOWN)) {
            controllerUsed = true
            PhoneStore.markControllerUsed(this)
        }
        if (key == RemoteKey.BACK) {
            if (event.repeatCount == 0) {
                when {
                    menuOpen -> closeMenu(null)
                    cardOpen -> closeCard()
                    winShown -> finish()
                    else -> input.down(key, 0, state(), now())?.forEach(::run)
                }
            }
            return true
        }
        if (menuOpen || cardOpen || winShown) {
            // The panels' buttons take arrows through Android's focus navigation.
            if (menuOpen && (key == RemoteKey.VOLUME_UP || key == RemoteKey.VOLUME_DOWN)) {
                if (event.repeatCount == 0) menu.nextTab(if (key == RemoteKey.VOLUME_UP) 1 else -1)
                return true
            }
            if (key == RemoteKey.OK) {
                if (event.repeatCount == 0) pressFocused()
                return true
            }
            if (key in ARROWS && !focusInOpenPanel()) {
                focusFirst()
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
        if (focused != null && focusInOpenPanel()) {
            focused.performClick()
        } else {
            focusFirst()
        }
    }

    /** True when the focused view sits inside the panel that is currently open. */
    private fun focusInOpenPanel(): Boolean {
        val focused = currentFocus ?: return false
        return isInside(focused, if (menuOpen) menu else if (cardOpen) cardPanel else winPanel)
    }

    private fun focusFirst() {
        when {
            menuOpen -> menu.focusFirst()
            cardOpen -> cardButton?.requestFocus()
            else -> firstWinButton?.requestFocus()
        }
    }

    private fun isInside(view: View, parent: View): Boolean {
        var v: View? = view
        while (v != null) {
            if (v === parent) return true
            v = v.parent as? View
        }
        return false
    }

    private fun run(c: Command) {
        when (c) {
            is Command.Press -> view.send { pressArrow(c.d) }
            is Command.Release -> view.send { releaseArrow(c.d) }
            Command.SkipGrowth -> view.send { skipGrowth() }
            Command.OpenMenu -> openMenu()
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

    // --- the menu ----------------------------------------------------------------------------

    private fun openMenu(first: PhoneTab? = null) {
        if (menuOpen) return
        menuOpen = true
        letGoOfStick()
        menuSettingsBefore = settings
        heldKeys.clear()
        view.send {
            paused = true
            clearKeys()
        }
        if (screenHeld) releaseScreen()
        if (winShown) hideWin()
        menu.show(first ?: reopenTab(menu.tab, menuClosedAt, now()))
        scrim.visibility = View.VISIBLE
        menu.visibility = View.VISIBLE
    }

    private fun closeMenu(action: MenuAction?) {
        if (!menuOpen) return
        menuOpen = false
        menuClosedAt = now()
        menu.visibility = View.GONE
        scrim.visibility = View.GONE
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

    private fun changePhoneSettings(next: PhoneSettings) {
        val before = phone
        phone = next
        PhoneStore.save(this, next)
        if (next.hold != before.hold) setTurns(turnsFor(lastDegrees, turns, next.hold, tall))
        if (next.touch != before.touch || next.hand != before.hand) {
            if (before.touch == TouchScheme.DRAG) view.send { dragEnd() }
            placeJoystick()
        }
        if (next.showTrace != before.showTrace) view.send { setShowTrace(next.showTrace) }
        if (next.hideBars != before.hideBars) applySystemBars()
    }

    // --- cards -------------------------------------------------------------------------

    /** The card shown now, so closing it can do what that card needs. */
    private var card: LaunchCard? = null
    /** The What's new card's notes and their text view, while it is the open card. */
    private var cardNews: WhatsNew? = null
    private var cardNotes: TextView? = null

    /**
     * Shows a card over the paused maze: a title, lines (plain or styled notes) and buttons, the
     * first of which takes a controller's focus.
     */
    private fun showCard(kind: LaunchCard, title: String, body: List<CharSequence>, buttons: List<Pair<String, () -> Unit>>) {
        if (cardOpen) closeCard()
        cardOpen = true
        card = kind
        heldKeys.clear()
        letGoOfStick()
        view.send {
            paused = true
            clearKeys()
        }
        if (screenHeld) releaseScreen()
        if (winShown) hideWin()
        cardPanel.removeAllViews()
        cardPanel.addView(label(title, 22f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
        }, LinearLayout.LayoutParams(MATCH, WRAP))
        for (line in body) {
            cardPanel.addView(label("", 16f, TEXT).apply {
                text = line
                setPadding(0, dp(10), 0, 0)
            }, LinearLayout.LayoutParams(MATCH, WRAP))
        }
        cardButton = null
        for ((text, action) in buttons) {
            val button = panelButton(text) { action() }
            if (cardButton == null) cardButton = button
            cardPanel.addView(button, LinearLayout.LayoutParams(MATCH, WRAP).apply { topMargin = dp(12) })
        }
        scrim.visibility = View.VISIBLE
        cardScroll.visibility = View.VISIBLE
    }

    /** Closes the card (Back, a tap outside, or its buttons) and resumes the game. */
    private fun closeCard() {
        if (!cardOpen) return
        cardOpen = false
        if (card == LaunchCard.HOW_TO_PLAY) PhoneStore.markHowToPlaySeen(this)
        card = null
        cardScroll.visibility = View.GONE
        scrim.visibility = View.GONE
        view.send { paused = false }
    }

    private fun showHowToPlay() =
        showCard(LaunchCard.HOW_TO_PLAY, "How to play", howToPlay(phone.touch), listOf("Play" to ::closeCard))

    private fun showWhatsNew(news: WhatsNew) {
        val notes = label("", 16f, DIM_TEXT)
        showCard(LaunchCard.WHATS_NEW, "Updated to ${news.version}", listOf(styledNotes(news.lines(), notes.paint)), listOf("Play" to ::closeCard))
        cardNews = news
        cardNotes = cardPanel.getChildAt(1) as? TextView // after the title
    }

    /** The check fetched the notes an open What's new card lacked: they replace its fallback in place. */
    private fun showArrivedNotes() {
        if (!cardOpen || card != LaunchCard.WHATS_NEW) return
        val news = cardNews?.let { withArrivedNotes(it, UpdateStore.loadSeen(this).notes) } ?: return
        cardNews = news
        cardNotes?.let { it.text = styledNotes(news.lines(), it.paint) }
    }

    private fun showUpdateCard(release: Release) {
        val entries = notesBetween(UpdateStore.loadSeen(this).notes, updates.current, release.version)
        val paint = label("", 16f, DIM_TEXT).paint
        val body = if (entries.isEmpty()) listOf<CharSequence>(RELEASES_TEXT) else listOf(styledNotes(WhatsNew(release.version, entries).lines(), paint))
        showCard(LaunchCard.UPDATE, "Labyrinth ${release.version} is available", body, listOf(
            "Update now" to {
                closeCard()
                openMenu(PhoneTab.ABOUT)
                updates.startUpdate(release)
            },
            "Dismiss" to {
                updates.dismiss(release)
                closeCard()
            },
        ))
    }

    private fun onUpdateChange() {
        showArrivedNotes()
        toolbar.setBadge(updates.offered != null)
        if (menuOpen) menu.changed()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleInstallReport(intent)
    }

    /**
     * InstallStatusActivity brings the game back when an update did not install: say so in About,
     * closing any card first. True when the report was taken.
     */
    private fun handleInstallReport(intent: Intent?): Boolean {
        if (intent?.getBooleanExtra(Updates.EXTRA_INSTALL_FAILED, false) != true) return false
        intent.removeExtra(Updates.EXTRA_INSTALL_FAILED)
        // Removing the extra does not reach the copy Android keeps for a recreated activity. This
        // is the guard: only an install this process committed is reported, and only once.
        if (!Updates.takeInstallReport()) return false
        updates.installFailed()
        closeCard()
        if (menuOpen) menu.show(PhoneTab.ABOUT) else openMenu(PhoneTab.ABOUT)
        return true
    }

    // --- win panel and toolbar ---------------------------------------------------------------

    private fun refresh() {
        val snap = view.snapshot ?: return
        toolbar.show(if (snap.phase == RoundPhase.GROW) null else snap.explored, snap.elapsed)
        if (!snap.winScreen) winDismissed = false
        if (snap.winScreen && !winShown && !winDismissed && !menuOpen && !cardOpen) {
            winShown = true
            heldKeys.clear()
            renderWin()
        } else if (!snap.winScreen && winShown) {
            hideWin()
        }
        val hold = snap.dotMoving && !menuOpen && !cardOpen
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

    private fun scroller(panel: LinearLayout, maxWidthDp: Int) = CappedScroll(this, dp(maxWidthDp)).apply {
        isFillViewport = false
        isVerticalScrollBarEnabled = false
        addView(panel, FrameLayout.LayoutParams(MATCH, WRAP))
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != REQUEST_TEST) return
        remote = GameStore.loadRemote(this) ?: remote
        val r = remote
        view.send { setRemote(r) }
        openMenu(PhoneTab.CONTROLS)
    }

    private companion object {
        const val REQUEST_TEST = 1
        const val WRAP = FrameLayout.LayoutParams.WRAP_CONTENT
        const val MATCH = FrameLayout.LayoutParams.MATCH_PARENT
    }
}
