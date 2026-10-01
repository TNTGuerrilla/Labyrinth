package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.game.c
import com.bydesigninteractive.labyrinth.game.forkGrid
import kotlin.math.abs
import kotlin.math.floor
import kotlin.random.Random
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

    @Test
    fun aLineEndingExactlyOnACornerWhileMovingLeftOrUpDoesNotRunPastIt() {
        assertEquals(listOf(c(4, 0), c(3, 0), c(3, 1), c(3, 2)), cellsAlong(4.5, 0.5, 3.0, 2.0))
    }

    @Test
    fun aLineStartingOutsideTheMaze() {
        assertEquals(listOf(c(-2, 0), c(-1, 0), c(0, 0), c(1, 0)), cellsAlong(-1.5, 0.5, 1.5, 0.5))
    }

    @Test
    fun randomLinesHaveCorrectProperties() {
        val rand = Random(1)
        repeat(1000) {
            val x0 = rand.nextDouble(-5.0, 15.0)
            val y0 = rand.nextDouble(-5.0, 15.0)
            val x1 = rand.nextDouble(-5.0, 15.0)
            val y1 = rand.nextDouble(-5.0, 15.0)
            val cells = cellsAlong(x0, y0, x1, y1)
            val startCell = c(floor(x0).toInt(), floor(y0).toInt())
            val endCell = c(floor(x1).toInt(), floor(y1).toInt())
            assertTrue("List starts at floor of start point", cells.first() == startCell)
            assertTrue("List ends at floor of end point", cells.last() == endCell)
            for (i in 1 until cells.size) {
                val prev = cells[i - 1]
                val curr = cells[i]
                val dx = abs(curr.x - prev.x)
                val dy = abs(curr.y - prev.y)
                assertTrue("Consecutive cells differ by exactly 1 in exactly one axis: $prev -> $curr", dx + dy == 1)
            }
            val expectedSize = abs(endCell.x - startCell.x) + abs(endCell.y - startCell.y) + 1
            assertEquals("Size equals |dx cells| + |dy cells| + 1", expectedSize, cells.size)
        }
    }

    @Test
    fun nonFiniteInputReturnsASingleCell() {
        val start = c(floor(0.5).toInt(), floor(0.5).toInt())
        assertEquals(listOf(start), cellsAlong(Double.NaN, 0.5, 1.5, 0.5))
        assertEquals(listOf(start), cellsAlong(0.5, Double.NaN, 1.5, 0.5))
        assertEquals(listOf(start), cellsAlong(0.5, 0.5, Double.POSITIVE_INFINITY, 0.5))
        assertEquals(listOf(start), cellsAlong(0.5, 0.5, 1.5, Double.NEGATIVE_INFINITY))
    }
}
