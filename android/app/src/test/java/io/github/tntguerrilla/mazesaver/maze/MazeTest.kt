package io.github.tntguerrilla.mazesaver.maze

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

class MazeTest {
    @Test
    fun gridBasics() {
        val g = Grid(3, 2)
        assertEquals(6, g.cells().count())
        assertEquals(setOf(Cell(1, 0), Cell(0, 1)), g.neighbors(Cell(0, 0)).toSet())
        g.carve(Cell(0, 0), Cell(1, 0))
        assertTrue(g.isOpen(Cell(1, 0), Cell(0, 0)))
        assertEquals(E, g.openDirs(Cell(0, 0)))
        assertEquals(W, g.openDirs(Cell(1, 0)))
        assertEquals(1, g.passageCount())
    }

    @Test(expected = IllegalArgumentException::class)
    fun gridRejectsZeroSize() {
        Grid(0, 3)
    }

    @Test
    fun edgeKeyIsOrderIndependent() {
        assertEquals(edgeKey(Cell(2, 1), Cell(1, 1)), edgeKey(Cell(1, 1), Cell(2, 1)))
        assertEquals(S, direction(Cell(0, 0), Cell(0, 1)))
    }

    @Test
    fun singleSnakeIsPerfect() {
        for ((cols, rows) in listOf(1 to 1, 2 to 2, 7 to 3, 20 to 15)) {
            for (seed in 0 until 5) {
                val g = Grid(cols, rows)
                singleSnake(g, Random(seed)).forEach { }
                assertPerfect(g)
            }
        }
    }

    @Test
    fun singleSnakeHeadMovesOneCellPerStep() {
        val g = Grid(8, 6)
        var head: Cell? = null
        for (e in singleSnake(g, Random(3))) {
            when (e) {
                is Start -> head = e.cell
                is Carve -> { assertEquals(head, e.a); head = e.b }
                is Retreat -> { assertEquals(head, e.from); head = e.to }
                is Finish -> assertEquals(head, e.cell)
                is Weld -> error("single snake never welds")
            }
        }
    }

    @Test
    fun multiSnakeIsPerfect() {
        for ((heads, cols, rows) in listOf(Triple(2, 10, 10), Triple(5, 30, 20), Triple(12, 40, 25))) {
            for (seed in 0 until 5) {
                val g = Grid(cols, rows)
                multiSnake(g, Random(seed), heads).forEach { }
                assertPerfect(g)
            }
        }
    }

    @Test
    fun multiSnakeClampsHeadsToCellCount() {
        val g = Grid(2, 2)
        assertEquals(4, multiSnake(g, Random(1), 10).toList().filterIsInstance<Start>().size)
        assertPerfect(g)
    }

    @Test
    fun weldsComeLastAndJoinEachRegionOnce() {
        val events = multiSnake(Grid(20, 20), Random(8), 6).toList()
        assertEquals(5, events.filterIsInstance<Weld>().size)
        assertTrue(events.dropWhile { it !is Weld }.all { it is Weld })
    }

    @Test
    fun chooseGeneratorUsesBothStyles() {
        val counts = (0 until 200).map { chooseGenerator(Grid(30, 30), Random(it)).first }
        assertTrue(counts.any { it == 1 })
        assertTrue(counts.any { it > 1 })
    }

    @Test
    fun chooseGeneratorScalesLeadsWithBoardSize() {
        // 1000 cells: upper bound is 4 + 1000 / 250 = 8.
        val counts = (0 until 400).map { chooseGenerator(Grid(40, 25), Random(it)).first }
        assertEquals(8, counts.max())
        assertEquals(1, counts.min())
    }

    @Test
    fun forcedHeads() {
        assertEquals(1, chooseGenerator(Grid(10, 10), Random(0), forcedHeads = 1).first)
        assertEquals(6, chooseGenerator(Grid(10, 10), Random(0), forcedHeads = 6).first)
        assertEquals(4, chooseGenerator(Grid(2, 2), Random(0), forcedHeads = 9).first)
    }
}
