// The screensaver itself. Android starts this when the TV goes idle; any remote button
// press ends it, since the dream is not interactive. When an update is waiting, a dim line
// sits in the margin the maze never uses and moves corner to corner so it cannot burn in.
package com.bydesigninteractive.labyrinth

import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.service.dreams.DreamService
import android.util.TypedValue
import android.view.Gravity
import android.widget.FrameLayout
import android.widget.TextView
import com.bydesigninteractive.labyrinth.update.Release
import com.bydesigninteractive.labyrinth.update.Updates

private const val CORNER_MS = 3L * 60 * 1000
private val CORNERS = intArrayOf(
    Gravity.BOTTOM or Gravity.END, Gravity.BOTTOM or Gravity.START,
    Gravity.TOP or Gravity.START, Gravity.TOP or Gravity.END,
)
private val NOTICE_COLOR = Color.rgb(95, 95, 95)

class LabyrinthDreamService : DreamService() {
    private val handler = Handler(Looper.getMainLooper())
    private var attached = false

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        isInteractive = false
        isFullscreen = true
        isScreenBright = true
        val root = FrameLayout(this)
        root.addView(MazeView(this, SettingsStore.load(this)))
        setContentView(root)
        attached = true
        Updates.check(this, force = false) { release -> if (attached && release != null) showNotice(root, release) }
    }

    override fun onDetachedFromWindow() {
        attached = false
        handler.removeCallbacksAndMessages(null)
        super.onDetachedFromWindow()
    }

    private fun showNotice(root: FrameLayout, release: Release) {
        val metrics = resources.displayMetrics
        val notice = TextView(this).apply {
            text = "Labyrinth ${release.version} is available. Open the Labyrinth app to update."
            setTextColor(NOTICE_COLOR)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f)
        }
        val params = FrameLayout.LayoutParams(FrameLayout.LayoutParams.WRAP_CONTENT, FrameLayout.LayoutParams.WRAP_CONTENT).apply {
            val side = metrics.widthPixels / 40
            val edge = metrics.heightPixels / 40
            setMargins(side, edge, side, edge)
        }
        root.addView(notice, params)
        placeNotice(notice, 0)
    }

    private fun placeNotice(notice: TextView, corner: Int) {
        (notice.layoutParams as FrameLayout.LayoutParams).gravity = CORNERS[corner % CORNERS.size]
        notice.requestLayout()
        handler.postDelayed({ placeNotice(notice, corner + 1) }, CORNER_MS)
    }
}
