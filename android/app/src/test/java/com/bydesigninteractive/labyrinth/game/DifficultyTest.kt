package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

class DifficultyTest {
    @Test
    fun presetsAreTheDesktopRanges() {
        assertEquals(mapOf("small" to (8 to 12), "medium" to (13 to 24), "large" to (25 to 48), "xl" to (49 to 96)), PRESETS)
        assertEquals(listOf("small", "medium", "large", "xl", "custom"), SIZES)
        assertEquals(4, MIN_CUSTOM)
        assertEquals(200, MAX_CUSTOM)
    }

    @Test
    fun ceilingIs80PercentOfTheShortSide() {
        assertEquals(832, ceiling(1920, 1040, coverage = 80))
        assertEquals(4, ceiling(3, 3, coverage = 80))
    }

    @Test
    fun ceilingFollowsTheCoverage() {
        assertEquals(1040, ceiling(1920, 1040))
        assertEquals(520, ceiling(1920, 1040, 50))
    }

    @Test
    fun sizeRangeClampsAndSorts() {
        assertEquals(25 to 48, sizeRange("large", 0, 0, 500))
        assertEquals(30 to 90, sizeRange("custom", 90, 30, 500))
        assertEquals(4 to 500, sizeRange("custom", 1, 99999, 500))
        assertEquals(49 to 60, sizeRange("xl", 0, 0, 60))
        assertEquals(20 to 20, sizeRange("xl", 0, 0, 20))
    }

    @Test
    fun pickShortCoversTheRange() {
        val rng = Random(1)
        val values = (0 until 300).map { pickShort("small", 0, 0, 1920, 1040, rng, coverage = 80) }.toSet()
        assertEquals((8..12).toSet(), values)
    }

    @Test
    fun pickShortNeverPassesTheTvCap() {
        val rng = Random(2)
        repeat(100) { assertTrue(pickShort("custom", 150, 400, 3840, 2160, rng) <= MAX_CUSTOM) }
    }

    @Test
    fun gridSizeFillsTheAspectRatio() {
        assertEquals(44 to 24, gridSize(24, 1920, 1040, coverage = 80))
        assertEquals(10 to 20, gridSize(10, 500, 1000, coverage = 80))
    }

    @Test
    fun gridAtTheCeilingHasAtLeastOnePixelPerCell() {
        val w = 1920
        val h = 1040
        for (coverage in listOf(50, 80, 100)) {
            val (cols, rows) = gridSize(ceiling(w, h, coverage), w, h, coverage)
            assertTrue(cols <= w * coverage / 100 && rows <= h * coverage / 100)
        }
    }

    @Test
    fun pickShortIsCappedByTheCoverage() {
        val rng = Random(1)
        assertEquals(setOf(100), (0 until 5).map { pickShort("custom", 100, 100, 200, 200, rng, coverage = 50) }.toSet())
        assertEquals(setOf(100), (0 until 5).map { pickShort("custom", 180, 180, 200, 200, rng, coverage = 50) }.toSet())
    }
}
