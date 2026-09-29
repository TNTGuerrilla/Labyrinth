package com.bydesigninteractive.labyrinth.maze

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

private val FAST = Settings(minCells = 4, maxCells = 6, genSpeed = 1000.0, solveSpeed = 500.0, holdSeconds = 0.5)
private const val DT = 1.0 / 60

private fun runUntil(board: Board, phase: Phase, limit: Int = 100000): List<Changes> {
    val changes = ArrayList<Changes>()
    repeat(limit) {
        changes.add(board.update(DT))
        if (board.phase == phase) return changes
    }
    throw AssertionError("never reached $phase")
}

class BoardTest {
    @Test
    fun geometryRulesHold() {
        val sizes = listOf(1920 to 1080, 3840 to 2160, 1280 to 720, 960 to 540, 1080 to 1920, 1000 to 1000)
        for ((w, h) in sizes) {
            val rng = Random(w * 7 + h)
            repeat(200) {
                val g = computeGeometry(w, h, 12, 40, rng, coverage = 80)
                val (nShort, nLong) = if (w >= h) g.rows to g.cols else g.cols to g.rows
                assertEquals(fill(minOf(w, h), 80) / nShort, g.cell)
                assertTrue(nShort <= nLong && nLong * g.cell <= fill(maxOf(w, h), 80))
                assertTrue(nShort in 12..40 && g.cell >= MIN_CELL_PX)
                assertEquals((w - g.width) / 2, g.x)
                assertEquals((h - g.height) / 2, g.y)
            }
        }
    }

    @Test
    fun fillTakesThePercentRoundedDown() {
        assertEquals(1080, fill(1080))
        assertEquals(1080, fill(1080, 100))
        assertEquals(540, fill(1080, 50))
        assertEquals(864, fill(1080, 80))
        assertEquals(49, fill(99, 50))
    }

    @Test
    fun geometryFollowsCoverage() {
        for (coverage in listOf(100, 50)) {
            val rng = Random(coverage)
            repeat(200) {
                val g = computeGeometry(1920, 1080, 12, 40, rng, coverage)
                assertEquals(fill(1080, coverage) / g.rows, g.cell)
                assertTrue(g.rows <= g.cols && g.width <= fill(1920, coverage))
                assertEquals((1920 - g.width) / 2, g.x)
                assertEquals((1080 - g.height) / 2, g.y)
            }
        }
        // Cell counts that divide the short side evenly fill it exactly at 100%.
        assertEquals(1080, computeGeometry(1920, 1080, 4, 4, Random(0)).height)
        assertEquals(540, computeGeometry(1920, 1080, 4, 4, Random(0), 50).height)
    }

    @Test
    fun noticeKeepsTheMazeWithinTheNoticeCoverage() {
        assertEquals(85, NOTICE_COVERAGE)
        for (seed in 0 until 20) {
            val free = Board(1920, 1080, FAST, Random(seed))
            runUntil(free, Phase.DOTS)
            assertEquals(1080, free.geometry!!.height)
            val capped = Board(1920, 1080, FAST, Random(seed)).apply { notice = true }
            runUntil(capped, Phase.DOTS)
            val g = capped.geometry!!
            assertTrue(g.height <= fill(1080, NOTICE_COVERAGE) && g.width <= fill(1920, NOTICE_COVERAGE))
            val half = Board(1920, 1080, FAST.copy(coverage = 50), Random(seed)).apply { notice = true }
            runUntil(half, Phase.DOTS)
            assertEquals(540, half.geometry!!.height)
        }
    }

    @Test
    fun tinyScreenStillValid() {
        for ((w, h) in listOf(10 to 10, 3 to 3, 40 to 12)) {
            val g = computeGeometry(w, h, 12, 40, Random(0), coverage = 80)
            assertEquals(2, minOf(g.cols, g.rows))
            assertTrue(g.width <= w && g.height <= h)
        }
    }

    @Test
    fun endpointsFarApart() {
        for ((cols, rows) in listOf(2 to 2, 4 to 4, 57 to 24, 3 to 50)) {
            for (seed in 0 until 300) {
                val (a, b) = chooseEndpoints(cols, rows, Random(seed))
                assertTrue(Math.abs(a.x - b.x) + Math.abs(a.y - b.y) >= (cols + rows) / 2)
            }
        }
    }

    @Test
    fun accumulatorKeepsFractionsAndCaps() {
        val acc = StepAccumulator(2.5)
        assertEquals(listOf(0, 1, 0, 1, 1, 0, 1, 1), List(8) { acc.take(0.25) })
        assertEquals(MAX_STEPS_PER_FRAME, StepAccumulator(1000.0).take(10.0))
    }

    @Test
    fun blackWaitsThenShowsDots() {
        val b = Board(400, 300, FAST, Random(1))
        assertTrue(b.update(0.01).clear)
        assertNull(b.geometry)
        b.update(BLACK_SECONDS - 0.02)
        assertEquals(Phase.BLACK, b.phase)
        val ch = b.update(0.02)
        assertEquals(Phase.DOTS, b.phase)
        assertEquals(setOf(b.start, b.end), ch.cells)
    }

    @Test
    fun fullCycleOrder() {
        val b = Board(400, 300, FAST, Random(2))
        val seen = arrayListOf(b.phase)
        while (!(seen.last() == Phase.BLACK && Phase.HOLD in seen)) {
            b.update(DT)
            if (b.phase != seen.last()) seen.add(b.phase)
        }
        assertEquals(listOf(Phase.BLACK, Phase.DOTS, Phase.GENERATE, Phase.SOLVE, Phase.HOLD, Phase.BLACK), seen)
    }

    @Test
    fun generationBuildsFullMazeWithRegions() {
        for (seed in 0 until 10) {
            val b = Board(400, 300, FAST, Random(seed))
            runUntil(b, Phase.SOLVE)
            val g = b.grid!!
            assertPerfect(g)
            assertEquals(g.cols * g.rows, b.regionOf.size)
            assertTrue(b.regionOf.values.all { it < b.hues.size })
            assertTrue(b.heads.isEmpty())
            assertEquals(b.start, b.dot)
        }
    }

    @Test
    fun solveLeavesTruePathBright() {
        for (seed in 0 until 10) {
            val b = Board(400, 300, FAST, Random(seed))
            runUntil(b, Phase.HOLD)
            assertTrue(b.solved)
            assertEquals(b.end, b.dot)
            val path = bfsPath(b.grid!!, b.start!!, b.end!!)
            assertEquals(path.zipWithNext { x, y -> edgeKey(x, y) }.toSet(), b.trail.filterValues { it }.keys)
        }
    }

    @Test
    fun changedCellsAreOnTheBoard() {
        val b = Board(400, 300, FAST, Random(5))
        for (ch in runUntil(b, Phase.HOLD)) for (c in ch.cells) assertTrue(b.grid!!.inBounds(c))
    }

    @Test
    fun holdThenClearsAndResets() {
        val b = Board(400, 300, FAST, Random(6))
        runUntil(b, Phase.HOLD)
        val ch = b.update(FAST.holdSeconds + 0.01)
        assertEquals(Phase.BLACK, b.phase)
        assertTrue(ch.clear && ch.cells.isEmpty())
        assertNull(b.geometry)
        assertTrue(b.trail.isEmpty())
        assertNull(b.dot)
    }

    @Test
    fun growthSpeedIsPerLead() {
        val s = Settings(minCells = 20, maxCells = 20, genSpeed = 10.0, solveSpeed = 500.0, holdSeconds = 0.5)
        val solo = Board(800, 600, s, Random(1), forcedLeads = 1)
        val swarm = Board(800, 600, s, Random(1), forcedLeads = 4)
        for (b in listOf(solo, swarm)) while (b.phase != Phase.GENERATE) b.update(0.01)
        solo.update(0.5)
        swarm.update(0.5)
        assertTrue(solo.regionOf.size <= 6)
        assertTrue(swarm.regionOf.size >= 14)
    }

    @Test
    fun dotGlidesBetweenSteps() {
        val slow = Settings(minCells = 4, maxCells = 6, genSpeed = 1000.0, solveSpeed = 10.0, holdSeconds = 0.5)
        val b = Board(400, 300, slow, Random(9))
        runUntil(b, Phase.SOLVE)
        assertNull(b.glideFrom)
        assertEquals(1.0, b.glideProgress, 0.0)
        while (b.glideFrom == null) b.update(DT)
        val first = b.glideProgress
        val ch = b.update(DT) // no new step at 10 steps per second, but the glide moves on
        assertTrue(b.glideProgress > first)
        assertTrue(ch.cells.containsAll(listOf(b.glideFrom, b.dot)))
        assertTrue(b.grid!!.isOpen(b.glideFrom!!, b.dot!!))
    }

    @Test
    fun glideEndsWhenSolved() {
        val b = Board(400, 300, FAST, Random(10))
        runUntil(b, Phase.HOLD)
        assertNull(b.glideFrom)
        assertEquals(1.0, b.glideProgress, 0.0)
        assertEquals(b.end, b.dot)
    }

    @Test
    fun weldsFlashThenExpire() {
        val b = Board(400, 300, FAST, Random(3), forcedLeads = 3)
        var sawWeld = false
        while (b.phase != Phase.SOLVE) {
            b.update(DT)
            sawWeld = sawWeld || b.welds.isNotEmpty()
        }
        assertTrue(sawWeld)
        b.update(WELD_FLASH_SECONDS + 0.01)
        assertTrue(b.welds.isEmpty())
    }

    @Test
    fun countsSolvedAndClearedMazes() {
        val board = Board(400, 300, FAST, Random(1))
        assertEquals(0, board.mazesSolved)
        runUntil(board, Phase.HOLD)
        assertEquals(1, board.mazesSolved)
        assertEquals(0, board.mazesCleared)
        runUntil(board, Phase.BLACK)
        assertEquals(1, board.mazesCleared)
    }

    @Test
    fun boardIsACellSource() {
        val source: CellSource = Board(1920, 1080, FAST, Random(1))
        runUntil(source as Board, Phase.SOLVE)
        assertTrue(source.grid != null && source.start != null && source.end != null)
        assertTrue(source.headCells.isEmpty())
    }
}
