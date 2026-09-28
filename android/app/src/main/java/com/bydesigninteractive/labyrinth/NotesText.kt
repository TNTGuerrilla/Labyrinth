// Release notes as styled text for a TextView: headings bold, bullets with their wrapped lines
// indented under the text. Call after the TextView's text size is set, since the indent is
// measured with its paint.
package com.bydesigninteractive.labyrinth

import android.graphics.Paint
import android.graphics.Typeface
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.LeadingMarginSpan
import android.text.style.StyleSpan
import com.bydesigninteractive.labyrinth.update.BULLET
import com.bydesigninteractive.labyrinth.update.LineKind
import com.bydesigninteractive.labyrinth.update.NoteLine

fun styledNotes(lines: List<NoteLine>, paint: Paint): CharSequence {
    val out = SpannableStringBuilder()
    val indent = paint.measureText(BULLET).toInt()
    lines.forEachIndexed { i, line ->
        val start = out.length
        when (line.kind) {
            LineKind.HEADING -> {
                out.append(line.text)
                out.setSpan(StyleSpan(Typeface.BOLD), start, out.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            LineKind.ITEM -> out.append(BULLET).append(line.text)
            LineKind.TEXT -> out.append(line.text)
            LineKind.BLANK -> {}
        }
        if (i < lines.size - 1) out.append('\n')
        // SPAN_EXCLUSIVE_EXCLUSIVE, not SPAN_PARAGRAPH: cutting the text to fit may end the span
        // mid-paragraph, which a paragraph-flagged span does not allow.
        if (line.kind == LineKind.ITEM) {
            out.setSpan(LeadingMarginSpan.Standard(0, indent), start, out.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }
    return out
}
