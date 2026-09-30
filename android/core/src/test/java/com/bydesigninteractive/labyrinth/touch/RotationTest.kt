package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import org.junit.Assert.assertEquals
import org.junit.Test

class RotationTest {
    @Test
    fun cleanSensorReadingsMapToTurns() {
        assertEquals(0, turnsFor(0, 0, Hold.AUTO, tall = true))
        assertEquals(3, turnsFor(90, 0, Hold.AUTO, tall = true))
        assertEquals(2, turnsFor(180, 0, Hold.AUTO, tall = true))
        assertEquals(1, turnsFor(270, 0, Hold.AUTO, tall = true))
        assertEquals(0, turnsFor(350, 1, Hold.AUTO, tall = true))
    }

    @Test
    fun aReadingBetweenQuarterTurnsKeepsTheCurrentTurns() {
        assertEquals(0, turnsFor(50, 0, Hold.AUTO, tall = true)) // 40 degrees from 90
        assertEquals(3, turnsFor(62, 0, Hold.AUTO, tall = true)) // 28 degrees from 90
        assertEquals(2, turnsFor(-1, 2, Hold.AUTO, tall = true)) // flat or unknown
    }

    @Test
    fun portraitAndLandscapeOnlyAllowTheirTurns() {
        assertEquals(listOf(0, 1, 2, 3), allowedTurns(Hold.AUTO, tall = true))
        assertEquals(listOf(0), allowedTurns(Hold.PORTRAIT, tall = true))
        assertEquals(listOf(3, 1), allowedTurns(Hold.LANDSCAPE, tall = true))
        assertEquals(listOf(3, 1), allowedTurns(Hold.PORTRAIT, tall = false))
        assertEquals(listOf(0), allowedTurns(Hold.LANDSCAPE, tall = false))
        assertEquals(0, turnsFor(90, 0, Hold.PORTRAIT, tall = true))
        assertEquals(3, turnsFor(0, 0, Hold.LANDSCAPE, tall = true)) // natural is not allowed: first allowed
        assertEquals(1, turnsFor(270, 3, Hold.LANDSCAPE, tall = true))
        assertEquals(3, turnsFor(-1, 0, Hold.LANDSCAPE, tall = true))
    }

    @Test
    fun directionsAsThePlayerSeesThemTurnOntoTheMaze() {
        assertEquals(N, toMaze(N, 0))
        assertEquals(E, toMaze(N, 1))
        assertEquals(N, toMaze(W, 1))
        assertEquals(S, toMaze(N, 2))
        assertEquals(E, toMaze(S, 3))
        assertEquals(W, toMaze(N, 3))
    }

    @Test
    fun arrowKeysTurnAndOtherKeysDoNot() {
        assertEquals(RemoteKey.UP, rotateKey(RemoteKey.UP, 0))
        assertEquals(RemoteKey.RIGHT, rotateKey(RemoteKey.UP, 1))
        assertEquals(RemoteKey.DOWN, rotateKey(RemoteKey.LEFT, 3))
        assertEquals(RemoteKey.LEFT, rotateKey(RemoteKey.RIGHT, 2))
        assertEquals(RemoteKey.OK, rotateKey(RemoteKey.OK, 1))
        assertEquals(RemoteKey.BACK, rotateKey(RemoteKey.BACK, 3))
    }

    @Test
    fun theToolbarSitsInTheStripAtTheTopOrTheLeftAsHeld() {
        // Tall: START is the top strip, END the bottom one.
        assertEquals(listOf(Strip.START, Strip.START, Strip.END, Strip.END), (0..3).map { toolbarStrip(it, tall = true) })
        // Wide: START is the left strip, END the right one.
        assertEquals(listOf(Strip.START, Strip.END, Strip.END, Strip.START), (0..3).map { toolbarStrip(it, tall = false) })
    }
}
