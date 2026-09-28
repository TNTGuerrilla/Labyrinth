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

    @Test
    fun sectionAndBoardNeverOverlap() {
        for ((w, h) in listOf(1920 to 1080, 3840 to 2160, 1280 to 720, 1080 to 1920, 1000 to 1000)) {
            val s = splitScreen(w, h)
            assertTrue(s.board.x == 0 && s.board.y == 0 && s.board.right <= w && s.board.bottom <= h)
            assertTrue(s.section.x >= 0 && s.section.y >= 0 && s.section.right <= w && s.section.bottom <= h)
            assertTrue(s.section.x >= s.board.right || s.section.y >= s.board.bottom)
        }
    }
}
