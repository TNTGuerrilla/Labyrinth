package com.bydesigninteractive.labyrinth.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private val REL = Release("1.2.0", "https://example.test/LabyrinthTV.apk", "ab".repeat(32))

class UpdateStateTest {
    @Test
    fun checksAreWeekly() {
        assertTrue(isDue(UpdateState(), 5))
        assertFalse(isDue(UpdateState(lastCheck = 100), 100 + CHECK_INTERVAL_MS - 1))
        assertTrue(isDue(UpdateState(lastCheck = 100), 100 + CHECK_INTERVAL_MS))
        assertTrue(isDue(UpdateState(lastCheck = 100), 50))
    }

    @Test
    fun aRecentSuccessfulCheckAnswersFromStoredState() {
        assertFalse(checkedRecently(null, 5))
        assertTrue(checkedRecently(1000, 1000))
        assertTrue(checkedRecently(1000, 1000 + RECHECK_INTERVAL_MS - 1))
        assertFalse(checkedRecently(1000, 1000 + RECHECK_INTERVAL_MS))
        assertFalse(checkedRecently(1000, 500)) // the clock went back: ask again
    }

    @Test
    fun missingNotesAskEvenWhenTheWeeklyCheckIsNotDueButNeverWithChecksOff() {
        assertTrue(asksGitHub(enabled = true, due = false, notesWanted = true))
        assertTrue(asksGitHub(enabled = true, due = true, notesWanted = true)) // one request serves both
        assertTrue(asksGitHub(enabled = true, due = true, notesWanted = false))
        assertFalse(asksGitHub(enabled = true, due = false, notesWanted = false))
        assertFalse(asksGitHub(enabled = false, due = false, notesWanted = true))
        assertFalse(asksGitHub(enabled = false, due = true, notesWanted = true))
    }

    @Test
    fun offersOnlyNewerUndismissedReleases() {
        assertEquals(REL, visibleUpdate(UpdateState(found = REL), "1.1.0"))
        assertNull(visibleUpdate(UpdateState(found = REL, dismissed = "1.2.0"), "1.1.0"))
        assertEquals(REL, visibleUpdate(UpdateState(found = REL, dismissed = "1.1.9"), "1.1.0"))
        assertNull(visibleUpdate(UpdateState(found = REL), "1.2.0"))
        assertNull(visibleUpdate(UpdateState(), "1.1.0"))
    }

    @Test
    fun pendingNoticeNeedsChecksOnAndAVisibleUpdate() {
        assertEquals(REL, pendingNotice(true, UpdateState(found = REL), "1.1.0"))
        assertNull(pendingNotice(false, UpdateState(found = REL), "1.1.0"))
        assertNull(pendingNotice(true, UpdateState(found = REL, dismissed = "1.2.0"), "1.1.0"))
        assertNull(pendingNotice(true, UpdateState(), "1.1.0"))
    }
}
