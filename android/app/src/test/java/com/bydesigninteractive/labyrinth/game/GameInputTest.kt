package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

private val PLAYING = InputState(menuOpen = false, phase = RoundPhase.PLAY, winScreen = false, mazeInProgress = true)
private val FRESH = PLAYING.copy(mazeInProgress = false)
private val GROWING = FRESH.copy(phase = RoundPhase.GROW)
private val MENU = PLAYING.copy(menuOpen = true)
private val WIN = FRESH.copy(phase = RoundPhase.WON, winScreen = true)

class GameInputTest {
    private val input = GameInput()

    @Test
    fun arrowsSteer() {
        assertEquals(listOf(Command.Press(E)), input.down(RemoteKey.RIGHT, 0, PLAYING, 0.0))
        assertEquals(listOf(Command.Release(N)), input.up(RemoteKey.UP))
    }

    @Test
    fun heldArrowRepeatsAreIgnored() {
        assertEquals(emptyList<Command>(), input.down(RemoteKey.RIGHT, 3, PLAYING, 0.0))
    }

    @Test
    fun okOpensTheMenu() {
        assertEquals(listOf(Command.OpenMenu), input.down(RemoteKey.OK, 0, PLAYING, 0.0))
        assertEquals(listOf(Command.OpenMenu), input.down(RemoteKey.OK, 0, GROWING, 0.0))
    }

    @Test
    fun anyOtherKeySkipsGrowth() {
        for (k in listOf(RemoteKey.UP, RemoteKey.LEFT, RemoteKey.OTHER)) {
            assertEquals(listOf(Command.SkipGrowth), input.down(k, 0, GROWING, 0.0))
        }
    }

    @Test
    fun volumeZoomsDuringPlayOnly() {
        assertEquals(listOf(Command.Zoom(1)), input.down(RemoteKey.VOLUME_UP, 0, PLAYING, 0.0))
        assertEquals(listOf(Command.Zoom(-1)), input.down(RemoteKey.VOLUME_DOWN, 0, GROWING, 0.0))
        assertNull(input.down(RemoteKey.VOLUME_UP, 0, MENU, 0.0))
        assertNull(input.down(RemoteKey.VOLUME_UP, 0, WIN, 0.0))
    }

    @Test
    fun otherKeysDuringPlayAreNotOurs() {
        assertNull(input.down(RemoteKey.OTHER, 0, PLAYING, 0.0))
        assertNull(input.up(RemoteKey.OTHER))
    }

    @Test
    fun backLeavesAtOnceWithoutAMazeInProgress() {
        assertEquals(listOf(Command.Leave), input.down(RemoteKey.BACK, 0, FRESH, 0.0))
        assertEquals(listOf(Command.Leave), input.down(RemoteKey.BACK, 0, GROWING, 0.0))
    }

    @Test
    fun backDuringAMazeAsksToBePressedAgain() {
        assertEquals(listOf(Command.BackHint), input.down(RemoteKey.BACK, 0, PLAYING, 10.0))
        assertEquals(listOf(Command.Leave), input.down(RemoteKey.BACK, 0, PLAYING, 11.5))
    }

    @Test
    fun aSecondBackTooLateAsksAgain() {
        input.down(RemoteKey.BACK, 0, PLAYING, 10.0)
        assertEquals(listOf(Command.BackHint), input.down(RemoteKey.BACK, 0, PLAYING, 12.5))
        assertEquals(listOf(Command.Leave), input.down(RemoteKey.BACK, 0, PLAYING, 13.0))
    }

    @Test
    fun aHeldBackDoesNotCountAsTheSecondPress() {
        assertEquals(listOf(Command.BackHint), input.down(RemoteKey.BACK, 0, PLAYING, 10.0))
        assertEquals(emptyList<Command>(), input.down(RemoteKey.BACK, 1, PLAYING, 10.5))
        assertEquals(listOf(Command.Leave), input.down(RemoteKey.BACK, 0, PLAYING, 11.0))
    }

    @Test
    fun theMenuGetsNavigationKeys() {
        assertEquals(listOf(Command.Menu(MenuKey.LEFT, 0)), input.down(RemoteKey.LEFT, 0, MENU, 0.0))
        assertEquals(listOf(Command.Menu(MenuKey.RIGHT, 9)), input.down(RemoteKey.RIGHT, 9, MENU, 0.0))
        assertEquals(listOf(Command.Menu(MenuKey.OK, 0)), input.down(RemoteKey.OK, 0, MENU, 0.0))
        assertEquals(listOf(Command.Menu(MenuKey.BACK, 0)), input.down(RemoteKey.BACK, 0, MENU, 0.0))
        assertNull(input.down(RemoteKey.OTHER, 0, MENU, 0.0))
    }

    @Test
    fun theWinScreenPicksAndConfirms() {
        assertEquals(listOf(Command.WinConfirm(0)), input.down(RemoteKey.OK, 0, WIN, 0.0))
        assertEquals(listOf(Command.WinPick(1)), input.down(RemoteKey.RIGHT, 0, WIN, 0.0))
        assertEquals(listOf(Command.WinConfirm(1)), input.down(RemoteKey.OK, 0, WIN, 0.0))
        assertEquals(listOf(Command.WinPick(0)), input.down(RemoteKey.LEFT, 0, WIN, 0.0))
        assertEquals(emptyList<Command>(), input.down(RemoteKey.UP, 0, WIN, 0.0))
        assertEquals(listOf(Command.Leave), input.down(RemoteKey.BACK, 0, WIN, 0.0))
    }

    @Test
    fun resetWinGoesBackToNewMaze() {
        input.down(RemoteKey.RIGHT, 0, WIN, 0.0)
        input.resetWin()
        assertEquals(0, input.winChoice)
    }
}
