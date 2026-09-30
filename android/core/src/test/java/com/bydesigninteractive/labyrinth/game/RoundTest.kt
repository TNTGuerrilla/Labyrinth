package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import com.bydesigninteractive.labyrinth.maze.assertPerfect
import com.bydesigninteractive.labyrinth.maze.bfsPath
import com.bydesigninteractive.labyrinth.maze.edgeKey
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

private fun branchRound(end: com.bydesigninteractive.labyrinth.maze.Cell = c(3, 1)) =
    Round.ofMaze(lineWithBranch(), c(0, 1), end, FAST)

class RoundTest {
    @Test
    fun growthMakesAPerfectMazeThenPlay() {
        val r = grown()
        assertPerfect(r.grid)
        assertTrue(r.heads.isEmpty())
        assertEquals(bfsPath(r.grid, r.start, r.end).size - 1, r.shortest)
    }

    @Test
    fun animatedGrowthReportsChangedCells() {
        val r = Round.create(20, 12, FAST, Random(3))
        val changed = HashSet<com.bydesigninteractive.labyrinth.maze.Cell>()
        repeat(3) { changed += r.update(1.0 / 60) }
        assertTrue(changed.isNotEmpty())
        assertEquals(RoundPhase.GROW, r.phase)
    }

    @Test
    fun skipGrowthFastForwardsWithinTheBudget() {
        var ticks = 0
        val r = Round.create(40, 30, FAST, Random(2)) { ticks++ * 0.001 }
        r.skipGrowth()
        r.update(1.0 / 60)
        assertEquals(RoundPhase.GROW, r.phase)
        assertTrue(r.regionOf.size in 1 until 1200)
        repeat(10000) { if (r.phase != RoundPhase.PLAY) r.update(1.0 / 60) }
        assertEquals(RoundPhase.PLAY, r.phase)
        assertPerfect(r.grid)
    }

    @Test
    fun instantModeStartsInFastForward() {
        val r = Round.create(6, 4, FAST.copy(animated = false), Random(4))
        assertTrue(r.fastForward)
        r.update(1.0 / 60)
        assertEquals(RoundPhase.PLAY, r.phase)
    }

    @Test
    fun noMovesWhileGrowing() {
        val r = Round.create(20, 12, FAST, Random(5))
        assertTrue(r.move(5.0, { _, _ -> null }).isEmpty())
        assertEquals(0, r.explored)
    }

    @Test
    fun movesCountCellsExploredAndBuildTheTrail() {
        val r = grown()
        val path = bfsPath(r.grid, r.start, r.end)
        val changed = r.move(10.0, PathSteer(path.subList(1, 3))::choose)
        assertEquals(2, r.explored)
        assertEquals(path.subList(0, 3), r.path.route)
        assertTrue(r.timerRunning)
        assertTrue(changed.containsAll(path.subList(0, 3)))
    }

    @Test
    fun backtrackingDoesNotCountAgain() {
        val r = grown()
        val path = bfsPath(r.grid, r.start, r.end)
        r.move(10.0, PathSteer(listOf(path[1], path[2], path[1], path[2]))::choose)
        assertEquals(2, r.explored)
    }

    @Test
    fun returningToTheStartDoesNotCount() {
        val r = grown()
        val path = bfsPath(r.grid, r.start, r.end)
        r.move(10.0, PathSteer(listOf(path[1], path[0]))::choose)
        assertEquals(1, r.explored)
    }

    @Test
    fun reachingTheEndWins() {
        val r = grown()
        r.move(1000.0, PathSteer(bfsPath(r.grid, r.start, r.end).drop(1))::choose)
        assertEquals(RoundPhase.WON, r.phase)
        assertEquals(r.shortest, r.explored)
        assertEquals(100, r.efficiency)
        assertFalse(r.timerRunning)
        assertEquals(r.end, r.mover.frm)
        assertFalse(r.mover.moving)
    }

    @Test
    fun assistedCellsAreCountedSeparately() {
        val r = grown()
        r.move(1000.0, PathSteer(bfsPath(r.grid, r.start, r.end).drop(1))::choose, assisted = true)
        assertEquals(0, r.explored)
        assertEquals(r.shortest, r.autoExplored)
        assertEquals(100, r.efficiency)
    }

    @Test
    fun detoursLowerEfficiency() {
        val r = branchRound()
        r.move(100.0, PathSteer(listOf(c(1, 1), c(1, 0), c(1, 1), c(2, 1), c(3, 1)))::choose)
        assertEquals(RoundPhase.WON, r.phase)
        assertEquals(3, r.shortest)
        assertEquals(4, r.explored)
        assertEquals(75, r.efficiency)
    }

    @Test
    fun timerStartsOnTheFirstMove() {
        val r = grown()
        r.tickTimer(1.0)
        assertEquals(0.0, r.elapsed, 0.0)
        r.move(0.6, PathSteer(bfsPath(r.grid, r.start, r.end).subList(1, 2))::choose)
        r.tickTimer(1.0)
        assertEquals(1.0, r.elapsed, 0.0)
    }

    @Test
    fun replayResetsPlayButKeepsTheMaze() {
        val r = grown()
        val start = r.start
        r.move(1000.0, PathSteer(bfsPath(r.grid, r.start, r.end).drop(1))::choose)
        r.assisted = true
        r.replay()
        assertEquals(RoundPhase.PLAY, r.phase)
        assertEquals(0, r.explored)
        assertEquals(0, r.autoExplored)
        assertEquals(0, r.hints)
        assertTrue(r.trail.isEmpty())
        assertEquals(start, r.dot)
        assertFalse(r.assisted)
    }

    @Test
    fun replayForgetsVisitedCells() {
        val r = grown()
        val path = bfsPath(r.grid, r.start, r.end)
        r.move(10.0, PathSteer(path.subList(1, 3))::choose)
        r.replay()
        r.move(10.0, PathSteer(path.subList(1, 3))::choose)
        assertEquals(2, r.explored)
    }

    @Test
    fun hintCountsAndExpires() {
        val r = grown()
        r.hint(3)
        assertEquals(1, r.hints)
        assertTrue(r.hintActive)
        assertEquals(bfsPath(r.grid, r.start, r.end).drop(1).take(3), r.hintRoute)
        r.update(HINT_SECONDS + 0.01)
        assertFalse(r.hintActive)
    }

    @Test
    fun flashAndWinOverlayTiming() {
        val r = grown()
        r.flash()
        assertTrue(r.flashActive)
        r.move(1000.0, PathSteer(bfsPath(r.grid, r.start, r.end).drop(1))::choose)
        assertTrue(r.winPulseActive)
        assertFalse(r.winOverlayVisible)
        r.update(WIN_OVERLAY_DELAY)
        assertTrue(r.winOverlayVisible)
    }

    @Test
    fun multicolorOffUsesOneHue() {
        val r = Round.create(10, 8, FAST.copy(multicolor = false), Random(7))
        assertTrue(r.hues.all { it == SINGLE_HUE })
        r.multicolor = true
        assertTrue(r.hues.contentEquals(r.regionHues))
    }

    @Test
    fun ofMazeStartsInPlay() {
        val r = branchRound()
        assertEquals(RoundPhase.PLAY, r.phase)
        assertEquals(3, r.shortest)
    }

    // --- late turns ---------------------------------------------------------------

    /** Walks to the fork at (1,1) and on toward (2,1), stopping [past] of the way there. */
    private fun pastTheFork(past: Double): Round {
        val r = branchRound(end = c(1, 0))
        r.move(1.0 + past, PathSteer(listOf(c(1, 1), c(2, 1)))::choose)
        return r
    }

    @Test
    fun lateTurnAfterTheMidpointTakesTheOvershootBack() {
        val r = pastTheFork(0.6)
        assertEquals(2, r.explored)
        assertTrue(r.lateTurn(N, 0.2))
        assertEquals(1, r.explored)
        assertFalse(r.trail.containsKey(edgeKey(c(1, 1), c(2, 1))))
        assertEquals(c(1, 1), r.dot)
        assertTrue(r.mover.returning)
        r.move(10.0, { cell, _ -> if (cell == c(1, 1)) c(1, 0) else null })
        assertEquals(RoundPhase.WON, r.phase)
        assertEquals(2, r.explored)
        assertEquals(100, r.efficiency)
    }

    @Test
    fun lateTurnBeforeTheMidpointJustReturns() {
        val r = pastTheFork(0.3)
        assertEquals(1, r.explored)
        assertTrue(r.lateTurn(N, 0.2))
        assertEquals(1, r.explored)
        assertTrue(r.trail.getValue(edgeKey(c(0, 1), c(1, 1))))
    }

    @Test
    fun lateTurnReportsTheCellsToRedraw() {
        val r = pastTheFork(0.6)
        r.lateTurn(N, 0.2)
        assertTrue(r.update(0.0).containsAll(listOf(c(1, 1), c(2, 1))))
    }

    @Test
    fun lateTurnOutsideTheWindowIsRefused() {
        val r = pastTheFork(0.6)
        r.update(0.3)
        assertFalse(r.lateTurn(N, 0.2))
        assertEquals(2, r.explored)
    }

    @Test
    fun lateTurnNeedsAnOpenSide() {
        val r = pastTheFork(0.6)
        assertFalse(r.lateTurn(S, 0.2))
        assertFalse(r.lateTurn(E, 0.2)) // the way it already went
        assertFalse(r.lateTurn(W, 0.2)) // turning around is a reverse, not a late turn
    }

    @Test
    fun lateTurnWithNoWindowIsRefused() {
        assertFalse(pastTheFork(0.6).lateTurn(N, 0.0))
    }

    @Test
    fun endWeldFlashesClearsLiveWeldsAndReportsTheirCells() {
        for (seed in 1..60) {
            val r = Round.create(20, 12, FAST.copy(maxLeads = 8), Random(seed))
            var steps = 0
            while (r.welds.isEmpty() && r.phase == RoundPhase.GROW && steps++ < 20000) r.update(1.0 / 60)
            if (r.welds.isEmpty()) continue
            val cells = HashSet<com.bydesigninteractive.labyrinth.maze.Cell>()
            for (edge in r.welds.keys) { cells.add(edge.a); cells.add(edge.b) }
            r.endWeldFlashes()
            assertTrue(r.welds.isEmpty())
            assertTrue(r.update(0.0).containsAll(cells))
            return
        }
        org.junit.Assert.fail("no seed produced a weld")
    }
}
