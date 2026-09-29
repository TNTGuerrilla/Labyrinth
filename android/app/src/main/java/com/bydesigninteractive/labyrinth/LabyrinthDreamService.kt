// The screensaver itself. Android starts this when the TV goes idle; any remote button
// press ends it, since the dream is not interactive. When an update is waiting, a dim line
// sits in the margin the maze keeps while it shows (see NOTICE_COVERAGE) and moves corner
// to corner so it cannot burn in.
// After an update, What's new shows as a fixed-size card (a normal View) beside a MazeView
// sized to the rest of the screen, counts down a minute, fades after the next solve, and the
// maze gets the whole screen back when its board goes black for the next maze.
package com.bydesigninteractive.labyrinth

import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.service.dreams.DreamService
import android.text.SpannableStringBuilder
import android.util.DisplayMetrics
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import com.bydesigninteractive.labyrinth.update.CLOSES_AFTER
import com.bydesigninteractive.labyrinth.update.CLOSES_IN
import com.bydesigninteractive.labyrinth.update.FADE_MS
import com.bydesigninteractive.labyrinth.update.MORE_TEXT
import com.bydesigninteractive.labyrinth.update.Release
import com.bydesigninteractive.labyrinth.update.SectionClock
import com.bydesigninteractive.labyrinth.update.Split
import com.bydesigninteractive.labyrinth.update.UpdateStore
import com.bydesigninteractive.labyrinth.update.Updates
import com.bydesigninteractive.labyrinth.update.WhatsNew
import com.bydesigninteractive.labyrinth.update.countdownSeconds
import com.bydesigninteractive.labyrinth.update.splitScreen
import kotlin.math.ceil

private const val CORNER_MS = 3L * 60 * 1000
private val CORNERS = intArrayOf(
    Gravity.BOTTOM or Gravity.END, Gravity.BOTTOM or Gravity.START,
    Gravity.TOP or Gravity.START, Gravity.TOP or Gravity.END,
)
private val NOTICE_COLOR = Color.rgb(95, 95, 95)

class LabyrinthDreamService : DreamService(), MazeListener {
    private val handler = Handler(Looper.getMainLooper())
    private var attached = false
    private var maze: MazeView? = null
    private var root: FrameLayout? = null
    private var section: View? = null
    private var clock: SectionClock? = null
    private var split: Split? = null
    private var restorePending = false
    private var notice: TextView? = null
    /** An update this dream's own check found: its notice shows once the board goes black. */
    private var pendingRelease: Release? = null
    private var footerWords: TextView? = null
    private var footerNumber: TextView? = null

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        isInteractive = false
        isFullscreen = true
        isScreenBright = true
        val root = FrameLayout(this)
        val current = Updates.currentVersion(this)
        // Decided now, from what earlier checks found, so the first maze already leaves the
        // notice its margin. An update found by this dream's own check caps the mazes from the
        // next one on, and its notice shows once the board goes black (onMazeCleared).
        val noticeShows = Updates.pendingNotice(this) != null
        val maze = MazeView(this, SettingsStore.load(this), notice = noticeShows)
        maze.listener = this
        val news = UpdateStore.startWhatsNew(this, current)
        if (news != null) {
            // Counted first: any remote button ends the dream, and an interrupted run must count.
            UpdateStore.countWhatsNewRun(this, current)
            val (w, h) = screenSize()
            val s = splitScreen(w, h)
            split = s
            // The GLSurfaceView gets only the board's box, so its surface, bitmap and texture
            // are that size and the maze is laid out there; the section is a normal View beside it.
            root.addView(maze, FrameLayout.LayoutParams(s.board.w, s.board.h).apply {
                leftMargin = s.board.x
                topMargin = s.board.y
            })
            val view = sectionView(news, s.section.h)
            root.addView(view, FrameLayout.LayoutParams(s.section.w, s.section.h).apply {
                leftMargin = s.section.x
                topMargin = s.section.y
            })
            section = view
            clock = SectionClock(SystemClock.uptimeMillis())
            tick()
        } else {
            root.addView(maze)
        }
        this.root = root
        this.maze = maze
        setContentView(root)
        attached = true
        Updates.check(this, force = false) { release ->
            if (!attached || release == null || notice != null) return@check
            if (noticeShows) {
                showNotice(root, release)
            } else {
                maze.setNotice(true)
                pendingRelease = release
            }
        }
    }

    override fun onDetachedFromWindow() {
        attached = false
        maze?.listener = null
        section?.animate()?.cancel()
        handler.removeCallbacksAndMessages(null)
        section = null
        clock = null
        restorePending = false
        pendingRelease = null
        super.onDetachedFromWindow()
    }

    private fun screenSize(): Pair<Int, Int> {
        val metrics = DisplayMetrics()
        @Suppress("DEPRECATION")
        windowManager.defaultDisplay.getRealMetrics(metrics)
        return metrics.widthPixels to metrics.heightPixels
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()

    private fun dimText(value: String, sizePx: Float) = TextView(this).apply {
        text = value
        setTextColor(NOTICE_COLOR)
        setTextSize(TypedValue.COMPLEX_UNIT_PX, sizePx)
    }

    /**
     * The card, sized by its layout params to the split's box. Text sizes follow the card's
     * height, as on Windows (body 1/29, title 1/20, padding 1/40), so the text scales with
     * the card; notes that do not fit are cut with the More at line.
     */
    private fun sectionView(news: WhatsNew, cardH: Int): LinearLayout {
        val body = maxOf(10, cardH / 29).toFloat()
        val pad = maxOf(6, cardH / 40)
        val notes = dimText("", body)
        notes.text = styledNotes(news.lines(), notes.paint)
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
            background = GradientDrawable().apply {
                setColor(Color.BLACK)
                setStroke(maxOf(1, dp(1)), NOTICE_COLOR)
            }
            addView(dimText("Labyrinth updated to ${news.version}", maxOf(12, cardH / 20).toFloat()).apply {
                typeface = Typeface.DEFAULT_BOLD
                setPadding(0, 0, 0, (body / 2).toInt())
            })
            addView(notes, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f))
            addView(footer(body), LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT))
            notes.post { cutToFit(notes) }
        }
    }

    private fun footer(sizePx: Float): LinearLayout {
        val words = dimText(CLOSES_IN, sizePx)
        val number = dimText("60", sizePx).apply {
            fontFeatureSettings = "tnum" // equal-width digits
            gravity = Gravity.END
            // As wide as the widest two-digit number, so the words never move.
            width = (10..99).maxOf { ceil(paint.measureText(it.toString())).toInt() }
        }
        footerWords = words
        footerNumber = number
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(words)
            addView(number)
        }
    }

    /** As many lines as fit; when some do not, the last rows become the More at line. */
    private fun cutToFit(view: TextView) {
        val layout = view.layout ?: return
        val fit = view.height / view.lineHeight
        if (layout.lineCount <= fit) return
        val moreRows = ceil(view.paint.measureText(MORE_TEXT) / view.width.coerceAtLeast(1)).toInt().coerceAtLeast(1)
        val keep = (fit - moreRows).coerceAtLeast(0)
        val end = if (keep == 0) 0 else layout.getLineEnd(keep - 1)
        view.text = SpannableStringBuilder(view.text.subSequence(0, end)).apply {
            while (isNotEmpty() && this[length - 1].isWhitespace()) delete(length - 1, length)
            if (isNotEmpty()) append('\n')
            append(MORE_TEXT)
        }
    }

    /** Once a second, on the second: the countdown, then "Closes after this maze". */
    private fun tick() {
        val c = clock ?: return
        val elapsed = SystemClock.uptimeMillis() - c.startedMs
        val seconds = countdownSeconds(elapsed)
        if (seconds == null) {
            footerWords?.text = CLOSES_AFTER
            footerNumber?.visibility = View.GONE
            return
        }
        footerNumber?.text = seconds.toString()
        handler.postDelayed({ tick() }, 1000 - elapsed % 1000)
    }

    override fun onMazeSolved() {
        if (!attached) return
        val view = section ?: return
        if (clock?.boardSolved(SystemClock.uptimeMillis()) != true) return
        view.animate().alpha(0f).setDuration(FADE_MS).withEndAction {
            // withEndAction does not run when the animation is cancelled (the dream ended),
            // so an interrupted fade is not counted as seen.
            root?.removeView(view)
            section = null
            split = null
            UpdateStore.markWhatsNewSeen(this, Updates.currentVersion(this))
            restorePending = true
            notice?.let { applyNoticeMargins(it) }
        }
    }

    override fun onMazeCleared() {
        if (!attached) return
        pendingRelease?.let { release ->
            // The next maze is laid out with the notice cap, so the line never covers it.
            pendingRelease = null
            root?.let { showNotice(it, release) }
        }
        if (!restorePending) return
        restorePending = false
        // The board just went black for its next maze: give the view the whole screen. Its
        // surface grows, and MazeRenderer starts a full-size board with no extra delay.
        maze?.layoutParams = FrameLayout.LayoutParams(FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT)
    }

    private fun showNotice(root: FrameLayout, release: Release) {
        val notice = TextView(this).apply {
            text = "Labyrinth ${release.version} is available. Open the Labyrinth app to update."
            setTextColor(NOTICE_COLOR)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
        }
        val params = FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT)
        root.addView(notice, params)
        this.notice = notice
        applyNoticeMargins(notice)
        placeNotice(notice, 0)
    }

    /** The watermark keeps to the board's area while the section shows, so it never covers it. */
    private fun applyNoticeMargins(notice: TextView) {
        val (w, h) = screenSize()
        val side = w / 40
        val edge = h / 40
        val s = split
        val right = if (s != null && s.board.w < w) w - s.board.right + side else side
        val bottom = if (s != null && s.board.h < h) h - s.board.bottom + edge else edge
        (notice.layoutParams as FrameLayout.LayoutParams).setMargins(side, edge, right, bottom)
        notice.requestLayout()
    }

    private fun placeNotice(notice: TextView, corner: Int) {
        (notice.layoutParams as FrameLayout.LayoutParams).gravity = CORNERS[corner % CORNERS.size]
        notice.requestLayout()
        handler.postDelayed({ placeNotice(notice, corner + 1) }, CORNER_MS)
    }
}
