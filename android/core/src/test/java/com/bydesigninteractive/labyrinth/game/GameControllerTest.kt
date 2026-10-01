package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.W
import com.bydesigninteractive.labyrinth.maze.edgeKey
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

private val TEST = GameSettings(glideSpeed = 10.0, turnPause = 0.2, lookahead = 0)

private fun controller(settings: GameSettings = TEST, remote: RemoteProfile = RemoteProfile(), end: com.bydesigninteractive.labyrinth.maze.Cell = c(3, 1)) =
    GameController(settings, remote).apply { start(Round.ofMaze(lineWithBranch(), c(0, 1), end, settings)) }

private fun GameController.frames(n: Int, dt: Double = 0.02) = repeat(n) { frame(dt) }

class GameControllerTest {
    @Test
    fun forkPauseAddsLagAndCooldown() {
        val g = controller(remote = RemoteProfile(arrowLagMs = 100, arrowRepeatCooldownMs = 50))
        assertEquals(0.35, g.forkPause, 1e-9)
    }

    @Test
    fun theDotWaitsAtTheForkForTheWholePause() {
        val g = controller(remote = RemoteProfile(arrowLagMs = 100, arrowRepeatCooldownMs = 50))
        g.pressArrow(E)
        g.frame(0.1) // one cell: arrives at the fork (1,1) and starts the 0.35 s pause
        assertEquals(c(1, 1), g.round.mover.frm)
        g.frames(3, 0.1)
        assertFalse(g.dotMoving)
        g.frame(0.1)
        assertTrue(g.dotMoving)
    }

    @Test
    fun aLatePressTurnsAtTheForkItJustPassed() {
        val g = controller(settings = TEST.copy(turnPause = 0.0), remote = RemoteProfile(arrowLagMs = 200))
        g.pressArrow(E)
        repeat(200) { if (g.round.mover.to != c(2, 1)) g.frame(0.02) }
        assertEquals(c(2, 1), g.round.mover.to) // just left the fork
        g.frames(3) // about 0.3 of a cell further
        g.pressArrow(N)
        assertTrue(g.round.mover.returning)
        g.frames(50)
        assertEquals(c(1, 0), g.round.dot)
        assertFalse(g.round.trail.containsKey(edgeKey(c(1, 1), c(2, 1))))
        assertEquals(2, g.round.explored)
    }

    @Test
    fun withoutLagThereIsNoLateTurn() {
        val g = controller(settings = TEST.copy(turnPause = 0.0))
        g.pressArrow(E)
        repeat(200) { if (g.round.mover.to != c(2, 1)) g.frame(0.02) }
        g.frames(3)
        g.pressArrow(N)
        assertFalse(g.round.mover.returning)
    }

    @Test
    fun pressingTheOppositeWayReverses() {
        val g = controller(settings = TEST.copy(turnPause = 0.0))
        g.pressArrow(E)
        g.frames(2)
        g.pressArrow(W)
        assertEquals(c(0, 1), g.round.mover.to)
        assertNull(g.keys.request)
    }

    @Test
    fun steadyHoldsReleaseAtOnce() {
        val g = controller()
        g.pressArrow(E)
        g.releaseArrow(E)
        assertNull(g.keys.wanted)
    }

    @Test
    fun stutteringHoldsAreSmoothedOver() {
        val g = controller(remote = RemoteProfile(arrowHoldGapMs = 100))
        g.pressArrow(E)
        g.keys.request = null
        g.releaseArrow(E)
        g.frame(0.1)
        assertEquals(E, g.keys.wanted) // still held: the grace is 0.15 s
        g.pressArrow(E) // the stutter's next "press" continues the hold
        assertNull(g.keys.request)
        g.releaseArrow(E)
        g.frame(0.1)
        assertEquals(E, g.keys.wanted)
        g.frame(0.1)
        assertNull(g.keys.wanted) // 0.2 s without a press: really released
    }

    @Test
    fun clearKeysDropsAPendingRelease() {
        val g = controller(remote = RemoteProfile(arrowHoldGapMs = 100))
        g.pressArrow(E)
        g.keys.request = null
        g.releaseArrow(E)
        g.clearKeys()
        g.pressArrow(E) // a fresh press, not the stutter continuing the old hold
        assertEquals(E, g.keys.request)
    }

    @Test
    fun anArrowDuringGrowthSkipsItWithoutSteering() {
        val g = GameController(TEST, RemoteProfile())
        g.start(Round.create(20, 12, TEST, Random(3)))
        g.pressArrow(E)
        assertTrue(g.round.fastForward)
        assertNull(g.keys.wanted)
    }

    /** Skips growth with an arrow, as the game screen does, then lets the maze finish. */
    private fun GameController.growWithArrowReleased(d: Int) {
        start(Round.create(6, 4, TEST, Random(3)))
        skipGrowth()
        releaseArrow(d)
        var t = 0.0
        while (round.phase == RoundPhase.GROW) {
            frame(0.01)
            t += 0.01
        }
        assertTrue(t < 0.15) // still inside the grace a stutter would get
    }

    @Test
    fun anArrowReleasedDuringGrowthDoesNotSwallowTheFirstPress() {
        val g = GameController(TEST, RemoteProfile(arrowHoldGapMs = 100))
        g.growWithArrowReleased(E)
        g.pressArrow(E)
        assertEquals(E, g.keys.request)
        assertEquals(E, g.keys.wanted)
    }

    @Test
    fun aHoldStartedAfterGrowthIsStillSmoothedOver() {
        val g = GameController(TEST, RemoteProfile(arrowHoldGapMs = 100))
        g.growWithArrowReleased(E)
        g.pressArrow(E)
        g.keys.request = null
        g.releaseArrow(E)
        g.frame(0.1)
        g.pressArrow(E) // the stutter's next "press" continues the hold
        assertNull(g.keys.request)
        assertEquals(E, g.keys.wanted)
    }

    @Test
    fun autoSolveDrivesTheShortestRouteAndStops() {
        val g = controller(end = c(3, 1))
        g.toggleAuto()
        assertTrue(g.autoSolving)
        repeat(500) { if (g.round.phase == RoundPhase.PLAY) g.frame(0.02) }
        assertEquals(RoundPhase.WON, g.round.phase)
        assertEquals(3, g.round.autoExplored)
        assertEquals(0, g.round.explored)
        assertFalse(g.autoSolving)
    }

    @Test
    fun anArrowStopsAutoSolve() {
        val g = controller()
        g.toggleAuto()
        g.frames(2)
        g.pressArrow(E)
        assertFalse(g.autoSolving)
    }

    @Test
    fun replayStopsAutoSolveAndDropsTheRequest() {
        val g = controller()
        g.toggleAuto()
        repeat(500) { if (g.round.phase == RoundPhase.PLAY) g.frame(0.02) }
        g.replay()
        assertEquals(RoundPhase.PLAY, g.round.phase)
        assertFalse(g.autoSolving)
        assertNull(g.keys.request)
    }

    @Test
    fun theTimerRuns() {
        val g = controller()
        g.pressArrow(E)
        g.frames(10)
        assertTrue(g.round.elapsed > 0)
    }

    @Test
    fun touchLeavesTheRemoteOutOfTheForkPause() {
        val g = controller(remote = RemoteProfile(arrowLagMs = 100, arrowRepeatCooldownMs = 50))
        g.swipe(E)
        assertTrue(g.touch)
        assertEquals(0.2, g.forkPause, 1e-9)
    }

    @Test
    fun aKeyPressEndsTouchSteering() {
        val g = controller(remote = RemoteProfile(arrowLagMs = 100, arrowRepeatCooldownMs = 50))
        g.swipe(E)
        g.pressArrow(E)
        assertFalse(g.touch)
        assertEquals(0.35, g.forkPause, 1e-9)
    }

    @Test
    fun aSwipeRunsToTheForkAndStopsThere() {
        val g = controller(settings = TEST.copy(followBends = false))
        g.swipe(E)
        g.frames(100) // 2 s: far longer than reaching the fork and its 0.2 s pause
        assertEquals(c(1, 1), g.round.dot)
        assertFalse(g.dotMoving)
    }

    @Test
    fun aSwipeFollowsBendsWithBendAssistOn() {
        val g = GameController(TEST, RemoteProfile()).apply { start(Round.ofMaze(forkGrid(), c(0, 1), c(2, 1), TEST)) }
        g.swipe(N)
        g.frames(100)
        assertEquals(c(1, 0), g.round.dot)
    }

    @Test
    fun withBendAssistOffASwipeStopsAtTheBend() {
        val s = TEST.copy(followBends = false)
        val g = GameController(s, RemoteProfile()).apply { start(Round.ofMaze(forkGrid(), c(0, 1), c(2, 1), s)) }
        g.swipe(N)
        g.frames(100)
        assertEquals(c(0, 0), g.round.dot)
        assertFalse(g.dotMoving)
        g.swipe(E)
        g.frames(100)
        assertEquals(c(1, 0), g.round.dot) // straight on to the fork, where it stops
    }

    @Test
    fun withBendAssistOffASwipeDuringTheRunTurnsAtTheBend() {
        val s = TEST.copy(followBends = false)
        val g = GameController(s, RemoteProfile()).apply { start(Round.ofMaze(forkGrid(), c(0, 1), c(2, 1), s)) }
        g.swipe(N)
        g.frames(2)
        g.swipe(E)
        g.frames(100)
        assertEquals(c(1, 0), g.round.dot)
    }

    @Test
    fun withBendAssistOffASwipeRunsStraightThroughACorridor() {
        val s = TEST.copy(followBends = false)
        val g = controller(settings = s, end = c(1, 0))
        g.swipe(E)
        g.frames(100)
        assertEquals(c(1, 1), g.round.dot) // the fork
        g.swipe(E)
        g.frames(100)
        assertEquals(c(3, 1), g.round.dot) // straight through (2,1) to the dead end
    }

    @Test
    fun aSwipeDuringTheRunIsTheTurnAtTheFork() {
        val g = controller()
        g.swipe(E)
        g.frames(2)
        g.swipe(N)
        g.frames(100)
        assertEquals(c(1, 0), g.round.dot) // took the side branch, never went on to (2,1)
        assertEquals(2, g.round.explored)
    }

    @Test
    fun swipingBackReverses() {
        val g = controller(settings = TEST.copy(turnPause = 0.0))
        g.swipe(E)
        g.frames(2)
        g.swipe(W)
        assertEquals(c(0, 1), g.round.mover.to)
        assertNull(g.keys.request)
    }

    @Test
    fun aSwipeDuringGrowthSkipsItWithoutSteering() {
        val g = GameController(TEST, RemoteProfile())
        g.start(Round.create(20, 12, TEST, Random(3)))
        g.swipe(E)
        assertTrue(g.round.fastForward)
        assertNull(g.keys.request)
    }

    @Test
    fun aTapWalksToAnUnvisitedForkButNoFurther() {
        val g = controller(end = c(1, 0))
        assertFalse(g.goTo(c(3, 1)))
        assertTrue(g.goTo(c(1, 1)))
        g.frames(100)
        assertEquals(c(1, 1), g.round.dot)
        assertFalse(g.dotMoving)
    }

    @Test
    fun aTapRunsBackThroughVisitedCellsAndDownACorridor() {
        val g = controller(end = c(1, 0))
        g.goTo(c(1, 1))
        g.frames(100)
        assertTrue(g.goTo(c(3, 1)))
        g.frames(100)
        assertEquals(c(3, 1), g.round.dot)
        assertEquals(3, g.round.explored)
    }

    @Test
    fun aRefusedTapLeavesTheDotAlone() {
        val g = controller(end = c(1, 0))
        assertFalse(g.goTo(c(3, 1)))
        assertFalse(g.routing)
        g.frames(50)
        assertEquals(c(0, 1), g.round.dot)
    }

    @Test
    fun aTapBehindTheDotTurnsItAround() {
        val g = controller(settings = TEST.copy(turnPause = 0.0), end = c(1, 0))
        g.goTo(c(1, 1))
        g.frames(2)
        assertTrue(g.goTo(c(0, 1)))
        assertEquals(c(0, 1), g.round.mover.to)
    }

    @Test
    fun aDragStopsAtTheFirstUnvisitedForkAndEndsWhenLifted() {
        val g = GameController(TEST, RemoteProfile()).apply { start(Round.ofMaze(forkGrid(), c(0, 1), c(2, 1), TEST)) }
        g.dragTo(c(2, 1))
        g.frames(100)
        assertEquals(c(1, 0), g.round.dot)
        g.dragTo(null)
        assertFalse(g.routing)
    }

    @Test
    fun keysSwipesAndTheJoystickCancelARoute() {
        val g = controller(end = c(1, 0))
        g.goTo(c(1, 1))
        g.pressArrow(E)
        assertFalse(g.routing)
        g.goTo(c(1, 1))
        g.swipe(E)
        assertFalse(g.routing)
        g.goTo(c(1, 1))
        g.holdTouch(E)
        assertFalse(g.routing)
    }

    @Test
    fun theJoystickHasNoRemoteLag() {
        val g = controller(settings = TEST.copy(followBends = false), remote = RemoteProfile(arrowLagMs = 100, arrowRepeatCooldownMs = 50))
        g.holdTouch(E)
        assertTrue(g.touch)
        assertEquals(0.2, g.forkPause, 1e-9)
        g.releaseTouch(E)
        assertNull(g.keys.wanted)
    }

    @Test
    fun theJoystickHeldThroughTheForkCarriesOnLikeARemote() {
        val g = controller(settings = TEST.copy(followBends = false, pauseAtForks = false), end = c(1, 0))
        g.holdTouch(E)
        g.frames(100)
        assertEquals(c(3, 1), g.round.dot)
    }

    @Test
    fun aTapBehindABackingOutDotRoutesFromWhereItIsHeading() {
        val g = controller(settings = TEST.copy(turnPause = 0.0), remote = RemoteProfile(arrowLagMs = 200))
        g.pressArrow(E)
        repeat(200) { if (g.round.mover.to != c(2, 1)) g.frame(0.02) }
        g.frames(3)
        g.pressArrow(N)
        assertTrue(g.round.mover.returning)
        val explored = g.round.explored
        assertTrue(g.goTo(c(0, 1)))
        g.frames(100)
        assertEquals(c(0, 1), g.round.dot)
        assertEquals(explored, g.round.explored)
    }

    @Test
    fun theJoystickRespectsBendAssistOff() {
        val s = TEST.copy(followBends = false)
        val g = GameController(s, RemoteProfile()).apply { start(Round.ofMaze(forkGrid(), c(0, 1), c(2, 1), s)) }
        g.holdTouch(N)
        g.frames(100)
        assertEquals(c(0, 0), g.round.dot)
        assertFalse(g.dotMoving)
    }

    @Test
    fun autoSolveAndReplayClearARoute() {
        val g = controller(end = c(1, 0))
        g.goTo(c(1, 1))
        g.toggleAuto()
        assertFalse(g.routing)
        g.toggleAuto()
        g.goTo(c(1, 1))
        assertTrue(g.routing)
        g.replay()
        assertFalse(g.routing)
    }

    @Test
    fun clearingKeysEndsARoute() {
        val g = controller(end = c(1, 0))
        g.goTo(c(1, 1))
        g.clearKeys()
        assertFalse(g.routing)
    }
}
