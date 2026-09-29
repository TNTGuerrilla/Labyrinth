package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.edgeKey
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

private fun walked(vararg cells: Cell): Trail {
    val t = Trail(cells[0])
    for (i in 1 until cells.size) t.move(cells[i - 1], cells[i])
    return t
}

class TrailTest {
    @Test
    fun forwardMovesAreBright() {
        val t = walked(c(0, 0), c(1, 0), c(2, 0))
        assertEquals(listOf(c(0, 0), c(1, 0), c(2, 0)), t.route)
        assertEquals(mapOf(edgeKey(c(0, 0), c(1, 0)) to true, edgeKey(c(1, 0), c(2, 0)) to true), t.edges)
    }

    @Test
    fun backingUpDimsTheEdgeLeftBehind() {
        val t = walked(c(0, 0), c(1, 0), c(2, 0), c(1, 0))
        assertEquals(c(1, 0), t.cell)
        assertFalse(t.edges.getValue(edgeKey(c(1, 0), c(2, 0))))
        assertTrue(t.edges.getValue(edgeKey(c(0, 0), c(1, 0))))
    }

    @Test
    fun walkingADimEdgeAgainBrightensIt() {
        val t = walked(c(0, 0), c(1, 0), c(0, 0), c(1, 0))
        assertTrue(t.edges.getValue(edgeKey(c(0, 0), c(1, 0))))
    }

    @Test(expected = IllegalArgumentException::class)
    fun moveMustStartAtTheCurrentCell() {
        Trail(c(0, 0)).move(c(1, 0), c(2, 0))
    }

    @Test
    fun undoingAForwardMoveRemovesIt() {
        val t = walked(c(0, 0), c(1, 0))
        val step = t.move(c(1, 0), c(2, 0))
        t.undo(c(1, 0), c(2, 0), step)
        assertEquals(listOf(c(0, 0), c(1, 0)), t.route)
        assertEquals(mapOf(edgeKey(c(0, 0), c(1, 0)) to true), t.edges)
    }

    @Test
    fun undoingABacktrackRestoresTheBrightEdge() {
        val t = walked(c(0, 0), c(1, 0), c(2, 0))
        val step = t.move(c(2, 0), c(1, 0))
        t.undo(c(2, 0), c(1, 0), step)
        assertEquals(listOf(c(0, 0), c(1, 0), c(2, 0)), t.route)
        assertTrue(t.edges.getValue(edgeKey(c(1, 0), c(2, 0))))
    }

    @Test
    fun undoingARewalkRestoresTheDimEdge() {
        val t = walked(c(0, 0), c(1, 0), c(0, 0))
        val step = t.move(c(0, 0), c(1, 0))
        t.undo(c(0, 0), c(1, 0), step)
        assertEquals(listOf(c(0, 0)), t.route)
        assertFalse(t.edges.getValue(edgeKey(c(0, 0), c(1, 0))))
    }
}
