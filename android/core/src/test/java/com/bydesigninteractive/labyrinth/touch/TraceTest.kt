package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.game.c
import com.bydesigninteractive.labyrinth.game.forkGrid
import com.bydesigninteractive.labyrinth.maze.Cell
import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min
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
    fun tiesInAllDirectionsWithCornerEndings() {
        // up-left: (2.5, 2.5) to (1.0, 1.0), both decrease
        assertEquals(listOf(c(2, 2), c(1, 2), c(1, 1)), cellsAlong(2.5, 2.5, 1.0, 1.0))
        // down-right: (0.5, 0.5) to (2.0, 2.0), both increase
        assertEquals(listOf(c(0, 0), c(1, 0), c(1, 1), c(2, 1), c(2, 2)), cellsAlong(0.5, 0.5, 2.0, 2.0))
        // up-right: (0.5, 2.5) to (2.0, 1.0), x increases y decreases, line is y = 3-x
        assertEquals(listOf(c(0, 2), c(1, 2), c(1, 1), c(2, 1)), cellsAlong(0.5, 2.5, 2.0, 1.0))
        // pure diagonal 45 degrees
        assertEquals(listOf(c(0, 0), c(1, 0), c(1, 1), c(2, 1), c(2, 2)), cellsAlong(0.5, 0.5, 2.5, 2.5))
    }

    @Test
    fun randomLinesHaveCorrectProperties() {
        val rand = Random(1)
        val offsets = listOf(0.0, 0.5)
        repeat(1000) {
            val x0 = rand.nextInt(-5, 15) + offsets.random(rand)
            val y0 = rand.nextInt(-5, 15) + offsets.random(rand)
            val x1 = rand.nextInt(-5, 15) + offsets.random(rand)
            val y1 = rand.nextInt(-5, 15) + offsets.random(rand)
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
            for (cell in cells) {
                assertTrue("Cell $cell is crossed by segment ($x0, $y0) to ($x1, $y1)",
                    segmentIntersectsCell(x0, y0, x1, y1, cell.x, cell.y))
            }
            verifyParametricOrdering(x0, y0, x1, y1, cells)
        }
    }

    @Test
    fun nonFiniteInputReturnsASingleCell() {
        assertEquals(listOf(c(0, 0)), cellsAlong(Double.NaN, 0.5, 1.5, 0.5))
        assertEquals(listOf(c(0, 0)), cellsAlong(0.5, Double.NaN, 1.5, 0.5))
        assertEquals(listOf(c(0, 0)), cellsAlong(0.5, 0.5, Double.POSITIVE_INFINITY, 0.5))
        assertEquals(listOf(c(0, 0)), cellsAlong(0.5, 0.5, 1.5, Double.NEGATIVE_INFINITY))
    }

    private fun segmentIntersectsCell(x0: Double, y0: Double, x1: Double, y1: Double, cellX: Int, cellY: Int): Boolean {
        val epsilon = 1e-9
        val rectLeft = cellX.toDouble()
        val rectRight = cellX + 1.0
        val rectBottom = cellY.toDouble()
        val rectTop = cellY + 1.0
        return liangBarskyClip(x0, y0, x1, y1, rectLeft, rectRight, rectBottom, rectTop, epsilon)
    }

    private fun liangBarskyClip(x0: Double, y0: Double, x1: Double, y1: Double,
                                 left: Double, right: Double, bottom: Double, top: Double,
                                 epsilon: Double): Boolean {
        var t0 = 0.0
        var t1 = 1.0
        val dx = x1 - x0
        val dy = y1 - y0
        val tX = arrayOf(0.0, 0.0)
        val tY = arrayOf(0.0, 0.0)
        if (abs(dx) > epsilon) {
            tX[0] = (left - x0) / dx
            tX[1] = (right - x0) / dx
            if (tX[0] > tX[1]) {
                val tmp = tX[0]
                tX[0] = tX[1]
                tX[1] = tmp
            }
            t0 = max(t0, tX[0])
            t1 = min(t1, tX[1])
            if (t0 > t1) return false
        } else {
            if (x0 < left || x0 > right) return false
        }
        if (abs(dy) > epsilon) {
            tY[0] = (bottom - y0) / dy
            tY[1] = (top - y0) / dy
            if (tY[0] > tY[1]) {
                val tmp = tY[0]
                tY[0] = tY[1]
                tY[1] = tmp
            }
            t0 = max(t0, tY[0])
            t1 = min(t1, tY[1])
            if (t0 > t1) return false
        } else {
            if (y0 < bottom || y0 > top) return false
        }
        return true
    }

    private fun verifyParametricOrdering(startX: Double, startY: Double, endX: Double, endY: Double, cells: List<Cell>) {
        if (cells.isEmpty()) return
        var lastT = -1.0
        val dx = endX - startX
        val dy = endY - startY
        for (cell in cells) {
            var entryT = 0.0
            if (abs(dx) > 1e-9) {
                val t = if (dx > 0) (cell.x - startX) / dx else (cell.x + 1 - startX) / dx
                entryT = max(entryT, t)
            }
            if (abs(dy) > 1e-9) {
                val t = if (dy > 0) (cell.y - startY) / dy else (cell.y + 1 - startY) / dy
                entryT = max(entryT, t)
            }
            assertTrue("Cell $cell entered at parameter $entryT, but previous was $lastT",
                entryT >= lastT - 1e-9)
            lastT = entryT
        }
    }
}
