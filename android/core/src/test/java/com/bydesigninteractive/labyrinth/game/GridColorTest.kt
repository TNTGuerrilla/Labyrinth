package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Test

class GridColorTest {
    private fun rgb(r: Int, g: Int, b: Int) = (0xFF shl 24) or (r shl 16) or (g shl 8) or b

    @Test
    fun theDefaultStrengthIsTodaysFaintGrid() {
        assertEquals(rgb(30, 32, 40), gridColor(20))
    }

    @Test
    fun weakestAndStrongest() {
        assertEquals(rgb(15, 16, 20), gridColor(10))
        assertEquals(rgb(150, 160, 200), gridColor(100))
    }

    @Test
    fun channelsRoundDown() {
        assertEquals(rgb(52, 56, 70), gridColor(35))
    }
}
