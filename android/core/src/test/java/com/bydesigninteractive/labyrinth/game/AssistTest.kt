package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AssistTest {
    @Test
    fun towardEndPointsOneStepCloser() {
        val g = forkGrid()
        val t = buildTowardEnd(g, c(2, 1))
        assertEquals(c(1, 0), t[c(1, 1)])
        assertEquals(c(2, 0), t[c(1, 0)])
        assertEquals(c(2, 1), t[c(2, 0)])
        assertFalse(t.containsKey(c(2, 1)))
    }

    @Test
    fun deadEndWithinSeesShortBranches() {
        val g = forkGrid()
        assertTrue(deadEndWithin(g, c(1, 0), c(1, 1), c(2, 1), 1))
        assertFalse(deadEndWithin(g, c(1, 0), c(2, 0), c(2, 1), 4)) // contains the end
        assertFalse(deadEndWithin(g, c(1, 0), c(1, 1), c(2, 1), 0)) // depth 0 hides nothing
        assertTrue(deadEndWithin(g, c(1, 0), c(0, 0), c(2, 1), 2))
        assertFalse(deadEndWithin(g, c(1, 0), c(0, 0), c(2, 1), 1)) // continues past depth 1
    }
}
