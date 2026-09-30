package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SwipeTest {
    private val t = SwipeTracker(24f)

    @Test
    fun aDirectionFiresOnceTheFingerHasMovedFarEnough() {
        t.down(0f, 0f)
        assertNull(t.move(10f, 0f))
        assertEquals(E, t.move(30f, 2f))
    }

    @Test
    fun screenUpIsNorthAndDownIsSouth() {
        t.down(100f, 100f)
        assertEquals(N, t.move(100f, 70f))
        t.down(100f, 100f)
        assertEquals(S, t.move(100f, 130f))
        t.down(100f, 100f)
        assertEquals(W, t.move(70f, 100f))
    }

    @Test
    fun aDiagonalWaitsUntilOneAxisClearlyLeads() {
        t.down(0f, 0f)
        assertNull(t.move(25f, 20f))
        assertEquals(E, t.move(40f, 20f))
    }

    @Test
    fun theSameDirectionFiresOnceButATurnFiresAgain() {
        t.down(0f, 0f)
        assertEquals(E, t.move(30f, 0f))
        assertNull(t.move(60f, 0f))
        assertEquals(N, t.move(60f, -30f))
        assertEquals(E, t.move(90f, -30f))
    }

    @Test
    fun liftingReportsWhetherTheTouchSteered() {
        t.down(0f, 0f)
        t.move(10f, 0f)
        assertFalse(t.up())
        t.down(0f, 0f)
        t.move(30f, 0f)
        assertTrue(t.up())
    }

    @Test
    fun aCancelledTouchFiresNothing() {
        t.down(0f, 0f)
        t.cancel()
        assertNull(t.move(100f, 0f))
    }
}
