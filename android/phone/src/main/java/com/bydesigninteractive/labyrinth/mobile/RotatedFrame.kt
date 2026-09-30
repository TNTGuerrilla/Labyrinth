package com.bydesigninteractive.labyrinth.mobile

import android.content.Context
import android.view.View.MeasureSpec
import android.view.ViewGroup
import android.widget.FrameLayout

/**
 * Shows [content] turned by [turns] clockwise quarter turns, sized to fill this frame as
 * turned (a quarter turn swaps its width and height). Touches reach the turned content in its
 * own coordinates, because ViewGroup maps them through the child's rotation.
 */
class RotatedFrame(context: Context) : ViewGroup(context) {
    val content = FrameLayout(context)

    var turns = 0
        set(value) {
            if (field == value) return
            field = value
            requestLayout()
        }

    init {
        addView(content)
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val w = MeasureSpec.getSize(widthMeasureSpec)
        val h = MeasureSpec.getSize(heightMeasureSpec)
        setMeasuredDimension(w, h)
        val (cw, ch) = if (turns % 2 == 0) w to h else h to w
        content.measure(MeasureSpec.makeMeasureSpec(cw, MeasureSpec.EXACTLY), MeasureSpec.makeMeasureSpec(ch, MeasureSpec.EXACTLY))
    }

    override fun onLayout(changed: Boolean, l: Int, t: Int, r: Int, b: Int) {
        val cw = content.measuredWidth
        val ch = content.measuredHeight
        val left = (r - l - cw) / 2
        val top = (b - t - ch) / 2
        content.layout(left, top, left + cw, top + ch)
        content.pivotX = cw / 2f
        content.pivotY = ch / 2f
        content.rotation = 90f * turns
    }
}
