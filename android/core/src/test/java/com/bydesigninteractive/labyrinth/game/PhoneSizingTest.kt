package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.random.Random

class PhoneSizingTest {
    @Test
    fun usesTheReportedPpiWhenItIsPlausible() {
        assertEquals(421.0, plausiblePpi(420f, 422f, 480), 1e-9)
    }

    @Test
    fun fallsBackToTheDensityBucketWhenThePpiIsNonsense() {
        assertEquals(480.0, plausiblePpi(0f, 0f, 480), 1e-9)
        assertEquals(480.0, plausiblePpi(420f, 1500f, 480), 1e-9)
        assertEquals(480.0, plausiblePpi(99f, 420f, 480), 1e-9)
    }

    @Test
    fun convertsPixelsToMillimetres() {
        assertEquals(25.4, pxToMm(400, 400.0), 1e-9)
    }

    @Test
    fun presetsAimAtTheirCellSizeWithinFifteenPercent() {
        // A short side of 70 mm: Small 8.75 cells, Medium 14, Large 20, XL 28.
        assertEquals(7 to 10, phoneShortRange("small", 20, 40, 70.0, 1000))
        assertEquals(12 to 16, phoneShortRange("medium", 20, 40, 70.0, 1000))
        assertEquals(17 to 23, phoneShortRange("large", 20, 40, 70.0, 1000))
        assertEquals(24 to 32, phoneShortRange("xl", 20, 40, 70.0, 1000))
    }

    @Test
    fun customSizesNeverGoBelowOneAndAHalfMillimetres() {
        // 70 mm / 1.5 mm = 46 cells at most.
        assertEquals(20 to 46, phoneShortRange("custom", 20, 300, 70.0, 1000))
        assertEquals(20 to 46, phoneShortRange("custom", 300, 20, 70.0, 1000))
        assertEquals(46 to 46, phoneShortRange("custom", 100, 200, 70.0, 1000))
    }

    @Test
    fun sizesAreAlsoCappedByPixels() {
        assertEquals(30 to 30, phoneShortRange("xl", 20, 40, 200.0, 30))
    }

    @Test
    fun aTinyScreenStillGetsTheSmallestMaze() {
        assertEquals(MIN_CUSTOM to MIN_CUSTOM, phoneShortRange("small", 20, 40, 3.0, 1000))
    }

    @Test
    fun phoneGridFillsThePlayArea() {
        // 1080 x 2160 px at 400 ppi: the short side is 68.58 mm, so Medium is 12 to 16 cells.
        val s = GameSettings(size = "medium")
        repeat(20) { seed ->
            val (cols, rows) = phoneGrid(s, 1080, 2160, 400.0, Random(seed))
            assertTrue(cols in 12..16)
            assertEquals(gridSize(cols, 1080, 2160, 100), cols to rows)
        }
    }

    @Test
    fun coverageShrinksTheShortSideInMillimetres() {
        // At 50% coverage the short side is 34.29 mm, so Medium is 6 to 8 cells.
        val s = GameSettings(size = "medium", coverage = 50)
        repeat(20) { seed ->
            val (cols, _) = phoneGrid(s, 1080, 2160, 400.0, Random(seed))
            assertTrue(cols in 6..8)
        }
    }
}
