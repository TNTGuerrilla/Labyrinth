package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.game.c
import com.bydesigninteractive.labyrinth.game.forkGrid
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TraceTest {
    // forkGrid: (0,1) up to the bend (0,0), east to the fork (1,0), which leads to (2,0) and (1,1).
    private val grid = forkGrid()

    @Test
    fun aFingerLineCrossesEveryCellOnTheWay() {
        assertEquals(listOf(c(0, 0), c(1, 0), c(2, 0), c(3, 0)), cellsAlong(0.5, 0.5, 3.5, 0.5))
        assertEquals(listOf(c(3, 0), c(2, 0), c(1, 0), c(0, 0)), cellsAlong(3.5, 0.5, 0.5, 0.5))
        assertEquals(listOf(c(0, 0), c(0, 1), c(0, 2)), cellsAlong(0.5, 0.2, 0.5, 2.9))
        assertEquals(listOf(c(0, 0), c(1, 0), c(1, 1), c(2, 1)), cellsAlong(0.5, 0.5, 2.5, 1.5))
        assertEquals(listOf(c(1, 1)), cellsAlong(1.2, 1.3, 1.8, 1.9))
    }

    @Test
    fun openNeighboursJoinTheTraceAndWallsDoNot() {
        val t = Trace()
        assertFalse(t.enter(grid, c(1, 1), c(0, 1))) // (0,1) and (1,1) are not connected
        assertTrue(t.enter(grid, c(0, 0), c(0, 1)))
        assertTrue(t.enter(grid, c(1, 0), c(0, 1)))
        assertFalse(t.enter(grid, c(2, 1), c(0, 1))) // not next door to (1,0)
        assertTrue(t.enter(grid, c(2, 0), c(0, 1)))
        assertEquals(listOf(c(0, 0), c(1, 0), c(2, 0)), t.cells)
    }

    @Test
    fun backtrackingErasesTheLastCell() {
        val t = Trace()
        t.enter(grid, c(0, 0), c(0, 1))
        t.enter(grid, c(1, 0), c(0, 1))
        t.enter(grid, c(2, 0), c(0, 1))
        assertTrue(t.enter(grid, c(1, 0), c(0, 1)))
        assertEquals(listOf(c(0, 0), c(1, 0)), t.cells)
        t.enter(grid, c(0, 0), c(0, 1))
        t.enter(grid, c(0, 1), c(0, 1))
        assertEquals(emptyList<Any>(), t.cells)
    }

    @Test
    fun theSameCellAgainChangesNothing() {
        val t = Trace()
        assertFalse(t.enter(grid, c(0, 1), c(0, 1)))
        t.enter(grid, c(0, 0), c(0, 1))
        assertFalse(t.enter(grid, c(0, 0), c(0, 1)))
        assertEquals(listOf(c(0, 0)), t.cells)
    }

    @Test
    fun cellsTheDotReachesLeaveTheTrace() {
        val t = Trace()
        t.enter(grid, c(0, 0), c(0, 1))
        t.enter(grid, c(1, 0), c(0, 1))
        t.reached(c(0, 0))
        assertEquals(listOf(c(1, 0)), t.cells)
        t.reached(c(2, 0)) // not the next cell: nothing happens
        assertEquals(listOf(c(1, 0)), t.cells)
    }
}
