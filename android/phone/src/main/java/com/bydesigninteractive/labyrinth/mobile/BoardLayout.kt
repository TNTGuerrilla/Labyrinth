package com.bydesigninteractive.labyrinth.mobile

import android.content.Context
import android.view.View
import android.view.View.MeasureSpec
import android.view.ViewGroup

/**
 * The physical layout, which never rotates: the maze view between two strips at the
 * screen's short ends (top and bottom of a tall screen, left and right of a wide one), each
 * [stripPx] thick. [onShape] hears whether the screen is tall, first on the first layout and
 * then whenever it changes (a foldable unfolding, a window resize).
 */
class BoardLayout(
    context: Context,
    private val stripPx: Int,
    private val board: View,
    private val start: View,
    private val end: View,
    private val onShape: (tall: Boolean) -> Unit,
) : ViewGroup(context) {
    private var shape: Boolean? = null

    init {
        addView(board)
        addView(start)
        addView(end)
    }

    private fun exactly(px: Int) = MeasureSpec.makeMeasureSpec(maxOf(0, px), MeasureSpec.EXACTLY)

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        val h = MeasureSpec.getSize(heightMeasureSpec)
        setMeasuredDimension(w, h)
        if (h >= w) {
            start.measure(exactly(w), exactly(stripPx))
            end.measure(exactly(w), exactly(stripPx))
            board.measure(exactly(w), exactly(h - 2 * stripPx))
        } else {
            start.measure(exactly(stripPx), exactly(h))
            end.measure(exactly(stripPx), exactly(h))
            board.measure(exactly(w - 2 * stripPx), exactly(h))
        }
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val w = r - l
        val h = b - t
        val tall = h >= w
        if (tall) {
            start.layout(0, 0, w, stripPx)
            board.layout(0, stripPx, w, h - stripPx)
            end.layout(0, h - stripPx, w, h)
        } else {
            start.layout(0, 0, stripPx, h)
            board.layout(stripPx, 0, w - stripPx, h)
            end.layout(w - stripPx, 0, w, h)
        }
        if (shape != tall) {
            shape = tall
            post { onShape(tall) }
        }
    }
}
