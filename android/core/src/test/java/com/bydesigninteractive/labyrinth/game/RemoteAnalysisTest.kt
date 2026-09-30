package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

private fun beats(count: Int, intervalMs: Double, first: Double = 1000.0) = List(count) { first + it * intervalMs }

/** What a remote with a cooldown lets through: presses closer than [cooldown] to the last registered one are lost. */
private fun throughCooldown(presses: List<Double>, cooldown: Double): List<Double> {
    val out = ArrayList<Double>()
    for (p in presses) if (out.isEmpty() || p - out.last() >= cooldown) out.add(p)
    return out
}

class RemoteAnalysisTest {
    @Test
    fun cleanRunGivesTheLag() {
        val b = beats(16, 1000.0)
        val jitter = listOf(-8.0, 5.0, 0.0, 12.0)
        val presses = b.mapIndexed { i, t -> t + 120 + jitter[i % 4] }
        assertEquals(123, lagMs(listOf(TempoRun(1000.0, b, presses)), need = 10)) // median 122.5 rounds up
    }

    @Test
    fun earlyPressesCountAsZero() {
        val b = beats(4, 1000.0)
        assertEquals(listOf(0.0, 0.0, 0.0, 0.0), offsets(b, b.map { it - 50 }, 1000.0))
    }

    @Test
    fun pressesFarFromEveryBeatAreIgnored() {
        val b = beats(4, 1000.0) // 1000 to 4000
        assertEquals(emptyList<Double>(), offsets(b, listOf(0.0, 10000.0), 1000.0))
    }

    @Test
    fun aBeatCountsOnlyOnce() {
        val b = beats(2, 1000.0)
        assertEquals(listOf(100.0), offsets(b, listOf(1100.0, 1150.0), 1000.0))
    }

    @Test
    fun aPlayerWhoMissesTooManyBeatsIsAskedToRepeat() {
        val b = beats(16, 1000.0)
        val presses = b.take(9).map { it + 100 }
        assertNull(lagMs(listOf(TempoRun(1000.0, b, presses)), need = 10))
    }

    @Test
    fun lagCombinesSeveralBlocks() {
        val runs = (0 until 4).map { k ->
            val b = beats(4, 1000.0, first = 1000.0 + k * 10000)
            TempoRun(1000.0, b, b.map { it + 100 + k * 10 })
        }
        assertEquals(115, lagMs(runs, need = 10))
    }

    @Test
    fun medianOfEvenAndOdd() {
        assertEquals(2.0, median(listOf(3.0, 1.0, 2.0)), 0.0)
        assertEquals(2.5, median(listOf(4.0, 1.0, 2.0, 3.0)), 0.0)
    }

    @Test
    fun aCooldownShowsAsAFloorUnderTheGaps() {
        val runs = listOf(2, 3, 4).map { perSecond ->
            val interval = 1000.0 / perSecond
            val b = beats(8, interval)
            TempoRun(interval, b, throughCooldown(b.map { it + 100 }, 400.0))
        }
        // The 3 and 4 per second blocks drop presses; their smallest registered gaps are 666.7 and 500 ms.
        assertEquals(500, cooldownMs(runs))
    }

    @Test
    fun randomMissesWithoutAFloorAreNotACooldown() {
        val runs = listOf(2, 3, 4).map { perSecond ->
            val interval = 1000.0 / perSecond
            val b = beats(8, interval)
            // Misses half the beats at 3 and 4 per second, but pairs of neighbors still land one interval apart.
            val presses = b.filterIndexed { i, _ -> perSecond < 3 || i % 4 < 2 }.map { it + 100 }
            TempoRun(interval, b, presses)
        }
        assertEquals(0, cooldownMs(runs))
    }

    @Test
    fun oneDroppingBlockIsNotEnough() {
        val runs = listOf(2, 3, 4).map { perSecond ->
            val interval = 1000.0 / perSecond
            val b = beats(8, interval)
            TempoRun(interval, b, throughCooldown(b.map { it + 100 }, 300.0))
        }
        assertEquals(0, cooldownMs(runs)) // only the 4-per-second block loses presses
    }

    @Test
    fun aSteadyHoldHasNoGap() {
        assertNull(holdGapMs(listOf(1000.0), listOf(4000.0)))
        assertNull(holdGapMs(emptyList(), emptyList()))
    }

    @Test
    fun aStutteringHoldReportsItsLongestGap() {
        assertEquals(150, holdGapMs(listOf(1000.0, 1300.0, 1650.0), listOf(1200.0, 1500.0, 4000.0)))
    }
}
