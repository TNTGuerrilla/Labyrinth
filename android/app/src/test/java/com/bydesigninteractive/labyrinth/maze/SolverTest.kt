package com.bydesigninteractive.labyrinth.maze

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

class SolverTest {
    private fun ends(e: SolveEvent): Pair<Cell, Cell> = when (e) {
        is Advance -> e.a to e.b
        is Backtrack -> e.a to e.b
        is Solved -> error("early Solved")
    }

    @Test
    fun findsTheUniquePath() {
        for (seed in 0 until 20) {
            val g = makeMaze(12, 9, seed)
            val events = solve(g, Cell(0, 0), Cell(11, 8), Random(seed + 100)).toList()
            assertTrue(events.dropLast(1).none { it is Solved })
            assertEquals(bfsPath(g, Cell(0, 0), Cell(11, 8)), (events.last() as Solved).path)
        }
    }

    @Test
    fun movesAreContiguousThroughOpenWalls() {
        val g = makeMaze(10, 10, 7)
        var pos = Cell(3, 4)
        for (e in solve(g, Cell(3, 4), Cell(9, 0), Random(1)).toList().dropLast(1)) {
            val (a, b) = ends(e)
            assertEquals(pos, a)
            assertTrue(g.isOpen(a, b))
            pos = b
        }
        assertEquals(Cell(9, 0), pos)
    }

    @Test
    fun brightTrailEqualsTruePath() {
        for (seed in 0 until 10) {
            val g = makeMaze(15, 11, seed)
            val trail = HashMap<Edge, Boolean>()
            val events = solve(g, Cell(0, 5), Cell(14, 5), Random(seed + 9)).toList()
            for (e in events.dropLast(1)) {
                val (a, b) = ends(e)
                trail[edgeKey(a, b)] = e is Advance
            }
            val path = (events.last() as Solved).path
            assertEquals(path.zipWithNext { a, b -> edgeKey(a, b) }.toSet(), trail.filterValues { it }.keys)
        }
    }

    @Test
    fun startEqualsEnd() {
        val g = makeMaze(3, 3, 0)
        assertEquals(listOf(Solved(listOf(Cell(1, 1)))), solve(g, Cell(1, 1), Cell(1, 1), Random(0)).toList())
    }

    @Test
    fun worksOnMultiSnakeMazes() {
        val g = Grid(20, 15)
        multiSnake(g, Random(4), 3).forEach { }
        val events = solve(g, Cell(0, 0), Cell(19, 14), Random(4)).toList()
        assertEquals(bfsPath(g, Cell(0, 0), Cell(19, 14)), (events.last() as Solved).path)
    }

    @Test
    fun takesWrongTurnsButFinishesReasonably() {
        var detoured = false
        for (seed in 0 until 20) {
            val g = makeMaze(60, 40, seed)
            val pathLen = bfsPath(g, Cell(0, 0), Cell(59, 39)).size
            val events = solve(g, Cell(0, 0), Cell(59, 39), Random(seed)).toList()
            assertTrue(events.size < 6 * pathLen + 400)
            if (events.any { it is Backtrack }) detoured = true
        }
        assertTrue(detoured)
    }

    @Test
    fun lookaheadZeroStillSolves() {
        for (seed in 0 until 10) {
            val g = makeMaze(20, 15, seed)
            val events = solve(g, Cell(0, 0), Cell(19, 14), Random(seed), lookahead = 0).toList()
            assertEquals(bfsPath(g, Cell(0, 0), Cell(19, 14)), (events.last() as Solved).path)
        }
    }

    @Test
    fun deterministicGivenSeed() {
        val g = makeMaze(20, 15, 3)
        val a = solve(g, Cell(0, 0), Cell(19, 14), Random(42)).toList()
        val b = solve(g, Cell(0, 0), Cell(19, 14), Random(42)).toList()
        assertEquals(a, b)
    }
}
