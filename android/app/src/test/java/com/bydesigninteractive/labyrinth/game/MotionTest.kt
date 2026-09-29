package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private val east: Chooser = { cell, _ -> if (cell.x < 3) Cell(cell.x + 1, cell.y) else null }
private val stay: Chooser = { _, _ -> null }

class MotionTest {
    @Test
    fun restsUntilTheChooserMoves() {
        val m = Mover(c(0, 0))
        assertEquals(emptyList<Move>(), m.advance(1.0, stay))
        assertFalse(m.moving)
        assertEquals(0.5 to 0.5, m.position())
    }

    @Test
    fun glidesAndSwitchesCellAtTheMidpoint() {
        val m = Mover(c(0, 0))
        assertEquals(emptyList<Move>(), m.advance(0.4, east))
        assertEquals(c(0, 0), m.cell)
        assertEquals(0.9, m.position().first, 1e-9)
        assertEquals(listOf(c(0, 0) to c(1, 0)), m.advance(0.2, east))
        assertEquals(c(1, 0), m.cell)
    }

    @Test
    fun longAdvanceCrossesSeveralCellsThenStops() {
        val m = Mover(c(0, 0))
        assertEquals(listOf(c(0, 0) to c(1, 0), c(1, 0) to c(2, 0), c(2, 0) to c(3, 0)), m.advance(10.0, east))
        assertEquals(c(3, 0), m.frm)
        assertFalse(m.moving)
    }

    @Test
    fun chooserSeesWhereTheDotCameFrom() {
        val calls = ArrayList<Pair<Cell, Cell?>>()
        val m = Mover(c(0, 0))
        m.advance(2.0) { cell, came -> calls.add(cell to came); if (cell == c(0, 0)) c(1, 0) else null }
        assertEquals(listOf(c(0, 0) to null, c(1, 0) to c(0, 0)), calls)
    }

    @Test
    fun lettingGoMidGlideFinishesAtTheNextCenter() {
        val m = Mover(c(0, 0))
        m.advance(0.3, east)
        assertEquals(listOf(c(0, 0) to c(1, 0)), m.advance(1.0, stay))
        assertEquals(c(1, 0), m.frm)
        assertFalse(m.moving)
    }

    @Test
    fun reverseBeforeTheMidpointKeepsTheCell() {
        val m = Mover(c(0, 0))
        m.advance(0.3, east)
        m.reverse()
        assertEquals(c(0, 0), m.cell)
        assertEquals(c(1, 0), m.frm)
        assertEquals(c(0, 0), m.to)
        assertEquals(emptyList<Move>(), m.advance(1.0, stay))
        assertEquals(c(0, 0), m.frm)
    }

    @Test
    fun reverseAfterTheMidpointMovesBack() {
        val m = Mover(c(0, 0))
        m.advance(0.7, east)
        m.reverse()
        assertEquals(c(1, 0), m.cell)
        assertEquals(listOf(c(1, 0) to c(0, 0)), m.advance(1.0, stay))
    }

    @Test
    fun reverseExactlyAtTheMidpointKeepsTheCell() {
        val m = Mover(c(0, 0))
        m.advance(0.5, east)
        assertEquals(c(1, 0), m.cell)
        m.reverse()
        assertEquals(c(1, 0), m.cell)
    }

    @Test
    fun nextCenterAndPlace() {
        val m = Mover(c(0, 0))
        m.advance(0.3, east)
        assertEquals(c(1, 0), m.nextCenter)
        m.place(c(3, 3))
        assertEquals(c(3, 3), m.cell)
        assertFalse(m.moving)
        assertNull(m.cameFrom)
    }

    @Test
    fun pullBackAfterTheMidpointReturnsWithoutAMove() {
        val m = Mover(c(0, 0))
        m.advance(0.7, east)
        m.pullBack()
        assertTrue(m.returning)
        assertEquals(c(0, 0), m.cell)
        assertEquals(c(0, 0), m.nextCenter)
        assertEquals(1.2, m.position().first, 1e-9)
        assertEquals(emptyList<Move>(), m.advance(1.0, stay))
        assertEquals(c(0, 0), m.frm)
        assertFalse(m.moving)
        assertFalse(m.returning)
    }

    @Test
    fun pullBackThenTheChooserPicksANewWayWithTheOldCameFrom() {
        val m = Mover(c(0, 0))
        m.advance(1.0, east) // rests at (1,0), came from (0,0)
        m.advance(0.3, east) // heading for (2,0)
        m.pullBack()
        val calls = ArrayList<Pair<Cell, Cell?>>()
        val moves = m.advance(1.0) { cell, came -> calls.add(cell to came); if (cell == c(1, 0)) c(1, 1) else null }
        assertEquals(c(1, 0) to c(0, 0), calls.first())
        assertEquals(listOf(c(1, 0) to c(1, 1)), moves)
    }

    @Test
    fun reverseIsIgnoredWhileReturning() {
        val m = Mover(c(0, 0))
        m.advance(0.3, east)
        m.pullBack()
        m.reverse()
        assertTrue(m.returning)
        assertEquals(c(0, 0), m.frm)
    }
}
