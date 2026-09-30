package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class JoystickTest {
    @Test
    fun eachWedgeIsAQuarterAroundItsAxis() {
        assertEquals(N, wedge(0f, -30f, 100f))
        assertEquals(E, wedge(30f, 0f, 100f))
        assertEquals(S, wedge(0f, 30f, 100f))
        assertEquals(W, wedge(-30f, 0f, 100f))
        assertEquals(E, wedge(30f, -29f, 100f))
        assertEquals(N, wedge(29f, -30f, 100f))
    }

    @Test
    fun theMiddleIsADeadZone() {
        assertNull(wedge(5f, 5f, 100f))
        assertNull(wedge(0f, 24f, 100f))
        assertEquals(S, wedge(0f, 26f, 100f))
    }

    @Test
    fun aThumbThatSlidesOffTheDiscStillCounts() {
        assertEquals(E, wedge(200f, 10f, 100f))
    }
}
