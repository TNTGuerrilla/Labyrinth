package com.bydesigninteractive.labyrinth.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private val NOTES = listOf(NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two"), NoteEntry("1.1.0", "One"))

class WhatsNewTest {
    @Test
    fun freshInstallRecordsTheVersionAndShowsNothing() {
        val (state, shown) = onStart(SeenState(notes = NOTES), "1.2.0")
        assertNull(shown)
        assertEquals("1.2.0", state.lastRunVersion)
    }

    @Test
    fun sameVersionOrDowngradeShowsNothing() {
        val same = SeenState("1.2.0", notes = NOTES)
        assertEquals(same to null, onStart(same, "1.2.0"))
        val newer = SeenState("1.3.0")
        assertEquals(newer to null, onStart(newer, "1.2.0"))
    }

    @Test
    fun olderStoredVersionShowsTheNewNotes() {
        val state = SeenState("1.1.0", notes = NOTES)
        val (after, shown) = onStart(state, "1.2.0")
        assertEquals(state, after)
        assertEquals(WhatsNew("1.2.0", listOf(NoteEntry("1.2.0", "Two"))), shown)
        assertEquals(listOf(NoteLine(LineKind.TEXT, "Two")), shown!!.lines())
    }

    @Test
    fun skippedVersionsGetHeadings() {
        val shown = onStart(SeenState("1.1.0", notes = NOTES), "1.3.0").second!!
        assertEquals(
            listOf(
                NoteLine(LineKind.HEADING, "Version 1.3.0"), NoteLine(LineKind.TEXT, "Three"), NoteLine(LineKind.BLANK),
                NoteLine(LineKind.HEADING, "Version 1.2.0"), NoteLine(LineKind.TEXT, "Two"),
            ),
            shown.lines(),
        )
    }

    @Test
    fun noNotesGivesTheFallback() {
        val shown = onStart(SeenState("1.1.0"), "1.2.0").second!!
        assertEquals(listOf(NoteLine(LineKind.TEXT, "Updated to version 1.2.0."), NoteLine(LineKind.TEXT, RELEASES_TEXT)), shown.lines())
    }

    @Test
    fun seenKeepsOnlyWhatThisUpdateBrought() {
        val state = markSeen(SeenState("1.1.0", 2, NOTES), "1.2.0")
        assertEquals(SeenState("1.2.0", 0, NOTES.take(2)), state)
        assertFalse(isPending(state, "1.2.0"))
        assertEquals(state, markSeen(state, "1.2.0"))
        assertEquals(WhatsNew("1.2.0", listOf(NoteEntry("1.2.0", "Two"))), runningNotes(state, "1.2.0"))
        assertEquals(listOf(NoteEntry("1.2.0", "Two")), runningNotes(SeenState("1.1.0", notes = NOTES), "1.2.0").entries)
    }

    @Test
    fun showsInAtMostThreeRuns() {
        var state = SeenState("1.1.0", notes = NOTES)
        for (run in 1 until SHOW_RUNS) {
            state = countRun(state, "1.2.0")
            assertEquals(run, state.runs)
            assertTrue(isPending(state, "1.2.0"))
        }
        state = countRun(state, "1.2.0")
        assertFalse(isPending(state, "1.2.0"))
    }

    @Test
    fun countdownRunsSixtyToOne() {
        assertEquals(60, countdownSeconds(0))
        assertEquals(60, countdownSeconds(999))
        assertEquals(59, countdownSeconds(1000))
        assertEquals(1, countdownSeconds(59_500))
        assertNull(countdownSeconds(60_000))
        assertEquals((60 downTo 1).toList(), (0 until 60).map { countdownSeconds(it * 1000L) })
    }

    @Test
    fun firstSolveAfterTheMinuteCloses() {
        val clock = SectionClock(100_000)
        assertFalse(clock.boardSolved(159_999))
        assertNull(clock.closedAtMs)
        assertTrue(clock.boardSolved(165_000))
        assertFalse(clock.boardSolved(170_000))
        assertEquals(165_000L, clock.closedAtMs)
    }

    private val sizes = listOf(1920 to 1080, 3440 to 1440, 2560 to 1440, 1200 to 1920, 1920 to 1200, 800 to 600)

    /** The rule written out: 540 x 690 at a 1440 px shorter side, scaled, clamped to 25% of the width (times the TV factor) and 80% of the height. */
    private fun expectedCard(w: Int, h: Int, factor: Double): Pair<Int, Int> {
        val scale = minOf(w, h) / 1440.0 * factor
        val cw = 540 * scale
        val ch = 690 * scale
        val k = minOf(1.0, w / 4.0 * factor / cw, h * 0.8 / ch)
        return Math.round(cw * k).toInt() to Math.round(ch * k).toInt()
    }

    @Test
    fun cardSizeFollowsTheRuleAndItsClamps() {
        assertEquals(540 to 690, cardSize(3440, 1440, 1.0))
        assertEquals(405 to 518, cardSize(1920, 1080, 1.0))
        assertEquals(506 to 647, cardSize(1920, 1080)) // the TV default: 1.25 times the monitor's
        for ((w, h) in sizes) {
            for (factor in listOf(1.0, TV_CARD_SCALE)) {
                val (cw, ch) = cardSize(w, h, factor)
                val (ew, eh) = expectedCard(w, h, factor)
                assertTrue("$w x $h at $factor: $cw x $ch", Math.abs(cw - ew) <= 1 && Math.abs(ch - eh) <= 1)
                assertTrue(cw <= w / 4.0 * factor && ch <= h * 0.8)
            }
        }
    }

    @Test
    fun cardAndBoardNeverOverlapAndCoverTheScreen() {
        for ((w, h) in sizes) {
            val s = splitScreen(w, h)
            val card = s.section
            val margin = minOf(w, h) / 40
            assertEquals(cardSize(w, h), card.w to card.h)
            assertTrue(card.x >= 0 && card.y >= 0 && card.right <= w && card.bottom <= h)
            if (w >= h) {
                assertEquals(Box(0, 0, w - card.w - 2 * margin, h), s.board)
                assertEquals(margin, card.x - s.board.right)
                assertEquals(margin, w - card.right)
                assertTrue(Math.abs(card.y - (h - card.bottom)) <= 1)
            } else {
                assertEquals(Box(0, 0, w, h - card.h - 2 * margin), s.board)
                assertEquals(margin, card.y - s.board.bottom)
                assertEquals(margin, h - card.bottom)
                assertTrue(Math.abs(card.x - (w - card.right)) <= 1)
            }
        }
    }
}
