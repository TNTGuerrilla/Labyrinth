// The remote test. Step 1 lines the click up with the picture (like Beat Saber's audio
// latency setting: no button timing, just move the click until it lands on the bounce).
// Steps 2 to 5 run blocks of beats (see RemoteScript) and record when keys went down and
// up; the analysis (RemoteAnalysis) turns that into a RemoteProfile, saved on OK at the end.
// Back leaves at any point without saving; opened from Play, it skips the test and starts
// the game with default timings, so the test is a recommendation, not a gate. Leaving the
// app mid-step restarts that step.
package com.bydesigninteractive.labyrinth.play

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.graphics.Typeface
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import com.bydesigninteractive.labyrinth.DIM_TEXT
import com.bydesigninteractive.labyrinth.TEXT
import com.bydesigninteractive.labyrinth.game.ARROW_LAG_BLOCKS
import com.bydesigninteractive.labyrinth.game.Block
import com.bydesigninteractive.labyrinth.game.BlockRun
import com.bydesigninteractive.labyrinth.game.COOLDOWN_BLOCKS
import com.bydesigninteractive.labyrinth.game.HOLD_BLOCKS
import com.bydesigninteractive.labyrinth.game.OK_LAG_BLOCKS
import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.game.Stage
import com.bydesigninteractive.labyrinth.game.cooldownMs
import com.bydesigninteractive.labyrinth.game.holdGapMs
import com.bydesigninteractive.labyrinth.game.lagMs

private const val MAX_SOUND_DELAY = 400
private const val BLOCK_START_MS = 800L
/** OK is ignored this long after a title or retry screen appears, so a trailing press cannot skip it. */
private const val SCREEN_GUARD_MS = 600L

private val STEPS = listOf(
    "Step 1 of 5: Sound" to "A dot bounces between two walls with a click on every bounce. " +
        "TVs often play sound a little late. Right plays the click earlier and left plays it later; " +
        "move it until it lands exactly on the bounce, then press OK.",
    "Step 2 of 5: Arrows" to "A dot travels into the box on a steady beat, and the box flashes as it arrives. " +
        "Press the arrow the dot is moving in, in time with the beat. Follow the rhythm rather than " +
        "waiting to see the dot arrive. Each arrow starts with two practice beats. " +
        "Gray dots are practice beats and don't count; the scored beats are green.",
    "Step 3 of 5: OK" to "The same, with the OK button.",
    "Step 4 of 5: Quick presses" to "The beat gets faster. Keep pressing on every beat for as long as you can. " +
        "Missing some at the fastest speeds is expected.",
    "Step 5 of 5: Holding" to "Hold the button down from the first beat and let go on the fourth.",
)

/** What the test is for. Only wording and margins differ; the timing and analysis are the same. */
enum class TestDevice(val title: String, val result: String, val ok: String, val soundNote: String) {
    REMOTE("Remote test", "Your remote", "OK", "TVs often play sound a little late."),
    CONTROLLER("Controller test", "Your controller", "A", "Phones and Bluetooth headphones often play sound a little late."),
}

private val OK_WORD = Regex("\\bOK\\b")

class RemoteTestActivity : Activity() {
    companion object {
        const val EXTRA_THEN_START = "then_start"
        const val EXTRA_DEVICE = "device"
    }

    private enum class Phase { LOADING, TITLE, SYNC, RUNNING, RETRY, RESULT }

    private val handler = Handler(Looper.getMainLooper())
    private val token = Any()
    private lateinit var testView: RemoteTestView
    private lateinit var titleView: TextView
    private lateinit var bodyView: TextView
    private lateinit var click: Click
    private var phase = Phase.LOADING
    /** Uptime when the current title or retry screen appeared. */
    private var shownAt = 0L
    private var step = 0
    private var soundDelayMs = 0
    private var nextHit = 0L
    private val queue = ArrayDeque<Block>()
    private var run: BlockRun? = null
    private val runs = ArrayList<BlockRun>()
    private var arrowLag = 0
    private var okLag = 0
    private val cooldowns = IntArray(3)
    private var holdArrow: Int? = null
    private var holdOk: Int? = null
    private var profile: RemoteProfile? = null
    private val device by lazy {
        TestDevice.entries.firstOrNull { it.name == intent.getStringExtra(EXTRA_DEVICE) } ?: TestDevice.REMOTE
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        testView = RemoteTestView(this)
        val phone = device == TestDevice.CONTROLLER
        titleView = text(if (phone) 24f else 30f, TEXT).apply { typeface = Typeface.DEFAULT_BOLD }
        bodyView = text(if (phone) 17f else 20f, DIM_TEXT)
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(if (phone) 24 else 96), dp(if (phone) 24 else 48), dp(if (phone) 24 else 96), 0)
            addView(titleView)
            addView(bodyView)
        }
        val footer = text(16f, DIM_TEXT).apply {
            text = if (thenPlay) "Back skips the test and starts the game." else "Back leaves the test."
        }
        setContentView(FrameLayout(this).apply {
            addView(testView)
            addView(column, FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.WRAP_CONTENT))
            addView(footer, FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL).apply { bottomMargin = dp(32) })
        })
        show(device.title, "Getting ready...")
        click = Click(this) { if (phase == Phase.LOADING) showTitle(0) }
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacksAndMessages(token)
        run = null
        if (phase == Phase.RUNNING || phase == Phase.SYNC) showTitle(step)
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        click.release()
        super.onDestroy()
    }

    // --- steps -----------------------------------------------------------------------

    private fun showTitle(i: Int) {
        step = i
        phase = Phase.TITLE
        shownAt = SystemClock.uptimeMillis()
        testView.clear()
        show(STEPS[i].first, STEPS[i].second + "\n\nPress OK to start.")
    }

    private fun beginStep() {
        if (step == 0) {
            startSync()
            return
        }
        runs.clear()
        queue.clear()
        queue.addAll(
            when (step) {
                1 -> ARROW_LAG_BLOCKS
                2 -> OK_LAG_BLOCKS
                3 -> COOLDOWN_BLOCKS
                else -> HOLD_BLOCKS
            },
        )
        phase = Phase.RUNNING
        nextBlock()
    }

    private fun startSync() {
        phase = Phase.SYNC
        val start = SystemClock.uptimeMillis() + 500
        testView.showSync(start)
        nextHit = start + 1000
        scheduleSyncClick()
        showSyncText()
    }

    private fun showSyncText() =
        show(STEPS[0].first, "Sound delay: $soundDelayMs ms\n\nRight: click earlier. Left: click later. OK when it lands on the bounce.")

    /** The next bounce's click, played soundDelayMs early; after a change, from the next bounce still ahead. */
    private fun scheduleSyncClick() {
        handler.removeCallbacksAndMessages(token)
        val now = SystemClock.uptimeMillis()
        while (nextHit - soundDelayMs <= now) nextHit += 1000
        handler.postAtTime({
            click.play()
            nextHit += 1000
            scheduleSyncClick()
        }, token, nextHit - soundDelayMs)
    }

    private fun nextBlock() {
        val block = queue.removeFirstOrNull() ?: return stepDone()
        val r = BlockRun(block, (SystemClock.uptimeMillis() + BLOCK_START_MS).toDouble())
        run = r
        testView.showRun(r)
        show(STEPS[step].first, "${block.prompt}\n\nGray dots are practice beats and don't count.")
        for (b in r.allBeats) handler.postAtTime({ click.play() }, token, b.toLong() - soundDelayMs)
        handler.postAtTime({
            runs.add(r)
            run = null
            nextBlock()
        }, token, r.endMs.toLong())
    }

    private fun stepDone() {
        testView.clear()
        fun stage(s: Stage) = runs.filter { it.block.stage == s }
        when (step) {
            1 -> arrowLag = lagMs(runs.map { it.tempoRun() }, need = 10) ?: return retry()
            2 -> okLag = lagMs(runs.map { it.tempoRun() }, need = 3) ?: return retry()
            3 -> {
                cooldowns[0] = cooldownMs(stage(Stage.COOLDOWN_REPEAT).map { it.tempoRun() })
                cooldowns[1] = cooldownMs(stage(Stage.COOLDOWN_ALTERNATE).map { it.tempoRun() })
                cooldowns[2] = cooldownMs(stage(Stage.COOLDOWN_OK).map { it.tempoRun() })
            }
            4 -> {
                holdArrow = stage(Stage.HOLD_ARROW).single().let { holdGapMs(it.presses, it.releases) }
                holdOk = stage(Stage.HOLD_OK).single().let { holdGapMs(it.presses, it.releases) }
            }
        }
        if (step < STEPS.lastIndex) showTitle(step + 1) else showResult()
    }

    private fun retry() {
        phase = Phase.RETRY
        shownAt = SystemClock.uptimeMillis()
        show(STEPS[step].first, "Too few presses landed near the beat. Follow the rhythm rather than " +
            "waiting for the dot, and try again.\n\nPress OK to try again.")
    }

    private fun showResult() {
        phase = Phase.RESULT
        val p = RemoteProfile(
            arrowLagMs = arrowLag, okLagMs = okLag, soundDelayMs = soundDelayMs,
            arrowRepeatCooldownMs = cooldowns[0], arrowAlternateCooldownMs = cooldowns[1], okCooldownMs = cooldowns[2],
            arrowHoldGapMs = holdArrow, okHoldGapMs = holdOk, testedAtMillis = System.currentTimeMillis(),
        )
        profile = p
        fun cooldown(ms: Int) = if (ms == 0) "none" else "$ms ms"
        fun hold(gap: Int?) = if (gap == null) "steady" else "stutters (gaps up to $gap ms)"
        show(device.result, listOf(
            "Arrow lag: ${p.arrowLagMs} ms",
            "OK lag: ${p.okLagMs} ms",
            "Sound delay: ${p.soundDelayMs} ms",
            "Cooldown, same arrow: ${cooldown(p.arrowRepeatCooldownMs)}",
            "Cooldown, alternating arrows: ${cooldown(p.arrowAlternateCooldownMs)}",
            "Cooldown, OK: ${cooldown(p.okCooldownMs)}",
            "Holding an arrow: ${hold(p.arrowHoldGapMs)}",
            "Holding OK: ${hold(p.okHoldGapMs)}",
        ).joinToString("\n") + "\n\nPress OK to finish.")
    }

    private fun finishTest() {
        profile?.let { GameStore.saveRemote(this, it) }
        setResult(RESULT_OK)
        startNext()
        finish()
    }

    /** Opened from Play, the caller names what starts after the test, whether it was finished or skipped. */
    private val thenStart: ComponentName? by lazy {
        if (Build.VERSION.SDK_INT >= 33) {
            intent.getParcelableExtra(EXTRA_THEN_START, ComponentName::class.java)
        } else {
            @Suppress("DEPRECATION")
            intent.getParcelableExtra(EXTRA_THEN_START)
        }
    }

    private val thenPlay: Boolean get() = thenStart != null

    private fun startNext() {
        thenStart?.let { startActivity(Intent().setComponent(it)) }
    }

    // --- keys ------------------------------------------------------------------------

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        val key = remoteKey(keyCode)
        if (key == RemoteKey.BACK) {
            if (event.repeatCount != 0) return true // a held Back skips once, not into the game too
            startNext()
            finish()
            return true
        }
        if (key == RemoteKey.VOLUME_UP || key == RemoteKey.VOLUME_DOWN || key == RemoteKey.OTHER) {
            return super.onKeyDown(keyCode, event)
        }
        val first = event.repeatCount == 0
        when (phase) {
            Phase.LOADING -> {}
            Phase.TITLE, Phase.RETRY ->
                if (key == RemoteKey.OK && first && event.eventTime - shownAt >= SCREEN_GUARD_MS) beginStep()
            Phase.SYNC -> when (key) {
                RemoteKey.LEFT, RemoteKey.RIGHT -> {
                    soundDelayMs = (soundDelayMs + if (key == RemoteKey.RIGHT) 10 else -10).coerceIn(0, MAX_SOUND_DELAY)
                    scheduleSyncClick()
                    showSyncText()
                }
                RemoteKey.OK -> if (first) {
                    handler.removeCallbacksAndMessages(token)
                    showTitle(1)
                }
                else -> {}
            }
            Phase.RUNNING -> if (first) run?.down(key, event.eventTime.toDouble())
            Phase.RESULT -> if (key == RemoteKey.OK && first) finishTest()
        }
        return true
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        val key = remoteKey(keyCode)
        if (key == RemoteKey.BACK) return true
        if (key == RemoteKey.VOLUME_UP || key == RemoteKey.VOLUME_DOWN || key == RemoteKey.OTHER) {
            return super.onKeyUp(keyCode, event)
        }
        if (phase == Phase.RUNNING) run?.up(key, event.eventTime.toDouble())
        return true
    }

    // --- views -----------------------------------------------------------------------

    private fun show(title: String, body: String) {
        val t = words(title)
        val b = words(body)
        titleView.text = t
        bodyView.text = b
    }

    /** The TV's wording, turned into the device's: its sound note, and its name for the OK button. */
    private fun words(text: String): String {
        if (device == TestDevice.REMOTE) return text
        return text.replace(TestDevice.REMOTE.soundNote, device.soundNote).replace(OK_WORD, device.ok)
    }

    private fun text(sizeSp: Float, color: Int) = TextView(this).apply {
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
        setTextColor(color)
        gravity = Gravity.CENTER
        setPadding(0, 0, 0, dp(12))
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
