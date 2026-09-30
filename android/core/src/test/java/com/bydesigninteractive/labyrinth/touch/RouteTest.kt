package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.game.c
import com.bydesigninteractive.labyrinth.game.forkGrid
import com.bydesigninteractive.labyrinth.game.lineWithBranch
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RouteTest {
    // lineWithBranch: (0,1)-(1,1)-(2,1)-(3,1), with a dead end (1,0) north of the fork (1,1).
    private val line = lineWithBranch()
    // forkGrid: (0,1) up to the bend (0,0), east to the fork (1,0), which leads to (2,0) and (1,1).
    private val fork = forkGrid()

    @Test
    fun theUniquePathRunsBetweenTwoCells() {
        assertEquals(listOf(c(0, 1), c(1, 1), c(1, 0)), uniquePath(line, c(0, 1), c(1, 0)))
        assertEquals(listOf(c(2, 1)), uniquePath(line, c(2, 1), c(2, 1)))
        assertEquals(emptyList<Any>(), uniquePath(line, c(0, 1), c(0, 0))) // (0,0) is not connected
    }

    @Test
    fun anUnvisitedForkEndsTheAllowedPart() {
        val path = uniquePath(fork, c(0, 1), c(2, 1))
        assertEquals(listOf(c(0, 1), c(0, 0), c(1, 0)), allowedPrefix(fork, path, setOf(c(0, 1))))
    }

    @Test
    fun visitedCellsAreAlwaysAllowed() {
        val path = uniquePath(fork, c(0, 1), c(2, 1))
        val all = setOf(c(0, 1), c(0, 0), c(1, 0), c(2, 0))
        assertEquals(path, allowedPrefix(fork, path, all))
    }

    @Test
    fun theFirstCellIsAlwaysAllowed() {
        // The dot is already heading there, even if it is an unvisited fork.
        assertEquals(listOf(c(1, 1)), allowedPrefix(line, listOf(c(1, 1), c(2, 1)), emptySet()))
    }

    @Test
    fun aTapMayEndAtAnUnvisitedForkButNotPassIt() {
        assertEquals(listOf(c(0, 1), c(1, 1)), tapRoute(line, setOf(c(0, 1)), c(0, 1), c(1, 1)))
        assertNull(tapRoute(line, setOf(c(0, 1)), c(0, 1), c(3, 1)))
    }

    @Test
    fun aTapRunsThroughVisitedCellsAndDownACorridor() {
        val visited = setOf(c(0, 1), c(1, 1))
        assertEquals(listOf(c(0, 1), c(1, 1), c(2, 1), c(3, 1)), tapRoute(line, visited, c(0, 1), c(3, 1)))
    }

    @Test
    fun aTapOnAnUnconnectedCellIsRefused() {
        assertNull(tapRoute(line, setOf(c(0, 1)), c(0, 1), c(0, 0)))
    }
}
