package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.Grid
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import com.bydesigninteractive.labyrinth.maze.bfsPath
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private val CROSS = arrayOf(c(0, 1) to c(1, 1), c(1, 1) to c(2, 1), c(1, 1) to c(1, 0), c(1, 1) to c(1, 2))
private val TEE = arrayOf(c(0, 1) to c(1, 1), c(1, 1) to c(1, 0), c(1, 1) to c(1, 2))
private val BEND = arrayOf(c(0, 0) to c(1, 0), c(1, 0) to c(1, 1))
private val FAR = c(9, 9) // an end outside these little grids

private fun held(vararg dirs: Int) = KeyboardSteer().apply { dirs.forEach { press(it) } }

/** Keys held with their press already used up (no pending request). */
private fun heldSinceBefore(vararg dirs: Int) = held(*dirs).apply { request = null }

private fun guided(k: KeyboardSteer, g: Grid, cell: Cell, came: Cell?, lookahead: Int = 0) =
    k.choose(g, cell, came, true, emptyList(), FAR, lookahead, 0.2)

private fun classic(k: KeyboardSteer, g: Grid, cell: Cell, came: Cell?, pause: Boolean = true) =
    k.choose(g, cell, came, false, emptyList(), FAR, 0, 0.2, pause)

class SteeringTest {
    @Test
    fun classicModeWithoutForkPausesIsTheDesktopRule() {
        val g = forkGrid()
        assertEquals(c(1, 0), held(E).choose(g, c(0, 0), null, false, emptyList(), FAR, 4, 0.2))
        assertNull(held(W).choose(g, c(0, 0), c(1, 0), false, emptyList(), FAR, 4, 0.2))
        assertNull(KeyboardSteer().choose(g, c(0, 0), null, false, emptyList(), FAR, 4, 0.2))
    }

    @Test
    fun latestPressWinsAndReleaseFallsBack() {
        val k = held(E, S)
        assertEquals(S, k.wanted)
        assertEquals(S, k.request)
        k.release(S)
        assertEquals(E, k.wanted)
        k.clear()
        assertNull(k.wanted)
        assertNull(k.request)
    }

    @Test
    fun freshPressIsTakenAtOnce() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        k.press(S)
        assertEquals(c(1, 2), guided(k, g, c(1, 1), c(0, 1)))
        assertNull(k.request)
    }

    @Test
    fun forkPausesThenCarriesStraightOn() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        assertNull(guided(k, g, c(1, 1), c(0, 1)))
        k.tick(0.1)
        assertNull(guided(k, g, c(1, 1), c(0, 1)))
        k.tick(0.15)
        assertEquals(c(2, 1), guided(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun pressDuringTheForkPauseTurns() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        assertNull(guided(k, g, c(1, 1), c(0, 1)))
        k.press(N)
        assertEquals(c(1, 0), guided(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun lettingGoDuringThePauseStops() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        guided(k, g, c(1, 1), c(0, 1))
        k.release(E)
        k.tick(1.0)
        assertNull(guided(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun tJunctionWaitsForAPress() {
        val g = gridOf(3, 3, *TEE)
        val k = heldSinceBefore(E)
        guided(k, g, c(1, 1), c(0, 1))
        k.tick(1.0)
        assertNull(guided(k, g, c(1, 1), c(0, 1)))
        k.press(S)
        assertEquals(c(1, 2), guided(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun corridorBendsFlowWithoutAPause() {
        assertEquals(c(1, 1), guided(heldSinceBefore(E), gridOf(2, 2, *BEND), c(1, 0), c(0, 0)))
    }

    @Test
    fun staleRequestIsDroppedAtABend() {
        val k = heldSinceBefore(E).apply { request = N }
        assertEquals(c(1, 1), guided(k, gridOf(2, 2, *BEND), c(1, 0), c(0, 0)))
        assertNull(k.request)
    }

    @Test
    fun obviousDeadEndsAreNotChoices() {
        val g = gridOf(4, 2, c(0, 0) to c(1, 0), c(1, 0) to c(2, 0), c(2, 0) to c(3, 0), c(1, 0) to c(1, 1))
        assertEquals(c(2, 0), heldSinceBefore(E).choose(g, c(1, 0), c(0, 0), true, emptyList(), c(3, 0), 4, 0.2))
    }

    @Test
    fun classicForkPausePausesThenFollowsTheHeldArrow() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        assertNull(classic(k, g, c(1, 1), c(0, 1)))
        k.tick(0.1)
        assertNull(classic(k, g, c(1, 1), c(0, 1)))
        k.tick(0.15)
        assertEquals(c(2, 1), classic(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun classicPressDuringThePauseGoesAtOnce() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        assertNull(classic(k, g, c(1, 1), c(0, 1)))
        k.press(N)
        assertEquals(c(1, 0), classic(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun classicPressBeforeArrivingSkipsThePause() {
        val g = gridOf(3, 3, *CROSS)
        val k = heldSinceBefore(E)
        k.press(S)
        assertEquals(c(1, 2), classic(k, g, c(1, 1), c(0, 1)))
    }

    @Test
    fun classicCorridorDoesNotPause() {
        val g = gridOf(3, 3, c(0, 1) to c(1, 1), c(1, 1) to c(2, 1))
        assertEquals(c(2, 1), classic(heldSinceBefore(E), g, c(1, 1), c(0, 1)))
    }

    @Test
    fun classicWithoutForkPausesDoesNotPause() {
        val g = gridOf(3, 3, *CROSS)
        assertEquals(c(2, 1), classic(heldSinceBefore(E), g, c(1, 1), c(0, 1), pause = false))
    }

    @Test
    fun resetRoundDropsTheRequestButKeepsHeldKeys() {
        val k = held(E)
        k.resetRound()
        assertNull(k.request)
        assertEquals(E, k.wanted)
    }

    @Test
    fun isReverseSpotsTurningAround() {
        assertTrue(isReverse(c(0, 0), c(1, 0), W))
        assertFalse(isReverse(c(0, 0), c(1, 0), E))
        assertFalse(isReverse(c(0, 0), null, W))
    }

    @Test
    fun autoSteerFollowsTheShortestRoute() {
        val g = forkGrid()
        val end = c(2, 1)
        val a = AutoSteer(buildTowardEnd(g, end), end)
        var cell = c(0, 1)
        val walked = ArrayList<Cell>()
        repeat(100) {
            val next = a.choose(cell) ?: return@repeat
            walked.add(next)
            cell = next
        }
        assertEquals(bfsPath(g, c(0, 1), end).drop(1), walked)
        assertTrue(a.done)
    }

    @Test
    fun autoSteerStartsFromADeadEnd() {
        val g = forkGrid()
        val a = AutoSteer(buildTowardEnd(g, c(2, 1)), c(2, 1))
        assertEquals(c(1, 0), a.choose(c(1, 1)))
        assertEquals(c(2, 0), a.choose(c(1, 0)))
    }

    @Test
    fun autoSteerAtTheEndIsDone() {
        val g = forkGrid()
        val a = AutoSteer(buildTowardEnd(g, c(2, 1)), c(2, 1))
        assertNull(a.choose(c(2, 1)))
        assertTrue(a.done)
    }

    @Test
    fun coastRunsThroughABendWithNothingHeld() {
        val g = forkGrid()
        val off = KeyboardSteer()
        assertNull(guided(off, g, c(0, 0), c(0, 1)))
        val on = KeyboardSteer().apply { coast = true }
        assertEquals(c(1, 0), guided(on, g, c(0, 0), c(0, 1)))
    }
}
