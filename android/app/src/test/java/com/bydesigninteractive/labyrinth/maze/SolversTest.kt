package com.bydesigninteractive.labyrinth.maze

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

class SolversTest {
    /** 3x2: (0,0)-(1,0)-(2,0) across the top, each with a spur down; (1,1) is a dead end. */
    private fun forkMaze(): Grid = Grid(3, 2).apply {
        carve(Cell(0, 0), Cell(1, 0))
        carve(Cell(1, 0), Cell(2, 0))
        carve(Cell(1, 0), Cell(1, 1))
        carve(Cell(0, 0), Cell(0, 1))
        carve(Cell(2, 0), Cell(2, 1))
    }

    /** Walks the events with a stack, checking each move, and returns the final stack. */
    private fun replay(events: List<SolveEvent>, start: Cell): List<Cell> {
        val stack = arrayListOf(start)
        for (e in events) {
            when (e) {
                is Advance -> {
                    assertEquals(stack.last(), e.a)
                    assertFalse(e.b in stack)
                    stack.add(e.b)
                }
                is Backtrack -> {
                    assertEquals(stack.last(), e.a)
                    assertEquals(stack[stack.size - 2], e.b)
                    stack.removeAt(stack.lastIndex)
                }
                is Solved -> {}
            }
        }
        return stack
    }

    @Test
    fun labelsAndDefault() {
        assertEquals(listOf("human", "dfs", "wall", "perfect"), SOLVER_LABELS.keys.toList())
        assertEquals(listOf("Human-like", "Depth-first", "Wall follower", "Perfect"), SOLVER_LABELS.values.toList())
        assertEquals("human", DEFAULT_SOLVER)
    }

    @Test
    fun everySolverReachesTheFinishThroughOpenPassages() {
        for (name in SOLVER_LABELS.keys) {
            for (seed in 0 until 12) {
                val g = makeMaze(13, 9, seed)
                val start = Cell(0, seed % 9)
                val end = Cell(12, 8 - seed % 9)
                val events = solveWith(name, g, start, end, Random(seed), 3).asSequence().toList()
                val last = events.last()
                assertTrue("$name $seed", last is Solved)
                assertFalse(events.dropLast(1).any { it is Solved })
                for (e in events.dropLast(1)) {
                    val (a, b) = when (e) { is Advance -> e.a to e.b; is Backtrack -> e.a to e.b; else -> error("") }
                    assertTrue(g.isOpen(a, b))
                }
                val stack = replay(events.dropLast(1), start)
                assertEquals(bfsPath(g, start, end), stack)
                assertEquals(stack, (last as Solved).path)
            }
        }
    }

    @Test
    fun startEqualsEnd() {
        for (name in SOLVER_LABELS.keys) {
            val g = makeMaze(4, 4, 1)
            assertEquals(listOf(Solved(listOf(Cell(2, 2)))), solveWith(name, g, Cell(2, 2), Cell(2, 2), Random(1)).asSequence().toList())
        }
    }

    @Test
    fun aWalledInStartGivesUpWithoutSolving() {
        for (name in SOLVER_LABELS.keys) {
            val events = solveWith(name, Grid(2, 1), Cell(0, 0), Cell(1, 0), Random(1)).asSequence().toList()
            assertFalse(name, events.any { it is Solved })
        }
    }

    @Test
    fun unknownNameUsesTheHumanLikeSolver() {
        val g = makeMaze(10, 8, 3)
        assertEquals(
            solveWith("human", g, Cell(0, 0), Cell(9, 7), Random(5)).asSequence().toList(),
            solveWith("nope", g, Cell(0, 0), Cell(9, 7), Random(5)).asSequence().toList(),
        )
    }

    @Test
    fun perfectWalksTheShortestRouteOnly() {
        val g = makeMaze(15, 11, 4)
        val route = bfsPath(g, Cell(0, 0), Cell(14, 10))
        val events = solveWith("perfect", g, Cell(0, 0), Cell(14, 10), Random(1)).asSequence().toList()
        assertEquals(route.zipWithNext { a, b -> Advance(a, b) }, events.dropLast(1))
    }

    @Test
    fun wallFollowerKeepsItsLeftHandOnTheWall() {
        val events = solveWith("wall", forkMaze(), Cell(2, 1), Cell(0, 1), Random(1)).asSequence().toList()
        assertEquals(
            listOf(
                Advance(Cell(2, 1), Cell(2, 0)),
                Advance(Cell(2, 0), Cell(1, 0)),
                Advance(Cell(1, 0), Cell(1, 1)),
                Backtrack(Cell(1, 1), Cell(1, 0)),
                Advance(Cell(1, 0), Cell(0, 0)),
                Advance(Cell(0, 0), Cell(0, 1)),
                Solved(listOf(Cell(2, 1), Cell(2, 0), Cell(1, 0), Cell(0, 0), Cell(0, 1))),
            ),
            events,
        )
    }

    @Test
    fun depthFirstSkipsADeadEndItCanSee() {
        val events = solveWith("dfs", forkMaze(), Cell(2, 1), Cell(0, 1), Random(1), 1).asSequence().toList()
        assertEquals(
            listOf(
                Advance(Cell(2, 1), Cell(2, 0)),
                Advance(Cell(2, 0), Cell(1, 0)),
                Advance(Cell(1, 0), Cell(0, 0)),
                Advance(Cell(0, 0), Cell(0, 1)),
                Solved(listOf(Cell(2, 1), Cell(2, 0), Cell(1, 0), Cell(0, 0), Cell(0, 1))),
            ),
            events,
        )
    }

    /**
     * A wrong branch that looks closer to the finish: from the start (0, 2) the corridor east
     * along row 2 ends at (width - 2, 2), one cell short of the finish (width - 1, 2). The real
     * route goes up to row 0, east, and back down.
     */
    private fun trapMaze(width: Int = 45): Grid = Grid(width, 3).apply {
        for (x in 0 until width - 2) carve(Cell(x, 2), Cell(x + 1, 2))
        carve(Cell(0, 2), Cell(0, 1))
        carve(Cell(0, 1), Cell(0, 0))
        for (x in 0 until width - 1) carve(Cell(x, 0), Cell(x + 1, 0))
        carve(Cell(width - 1, 0), Cell(width - 1, 1))
        carve(Cell(width - 1, 1), Cell(width - 1, 2))
    }

    /** It follows the tempting wrong branch all the way (43 cells) before backing out of it in one run. */
    @Test
    fun depthFirstHasNoDetourLimit() {
        val events = solveWith("dfs", trapMaze(), Cell(0, 2), Cell(44, 2), Random(1), 0).asSequence().toList()
        assertEquals((0 until 43).map { Advance(Cell(it, 2), Cell(it + 1, 2)) }, events.subList(0, 43))
        assertEquals((0 until 43).reversed().map { Backtrack(Cell(it + 1, 2), Cell(it, 2)) }, events.subList(43, 86))
        assertEquals(Advance(Cell(0, 2), Cell(0, 1)), events[86])
        assertTrue(events.last() is Solved)
    }

    @Test
    fun depthFirstNeverEntersAVisibleDeadEnd() {
        for (lookahead in listOf(1, 3, 6)) {
            for (seed in 0 until 8) {
                val g = makeMaze(14, 10, seed)
                val end = Cell(13, 9)
                for (e in solveWith("dfs", g, Cell(0, 0), end, Random(seed), lookahead)) {
                    if (e is Advance) assertFalse(scanBranch(g, e.a, e.b, end, lookahead).first)
                }
            }
        }
    }
}
