package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder

class RemoteScriptTest {
    @Test
    fun arrowLagIsFourArrowsOfFourBeats() {
        assertEquals(listOf(RemoteKey.UP, RemoteKey.RIGHT, RemoteKey.DOWN, RemoteKey.LEFT), ARROW_LAG_BLOCKS.map { it.keys.single() })
        assertEquals(16, ARROW_LAG_BLOCKS.sumOf { it.beats })
        assertTrue(ARROW_LAG_BLOCKS.all { it.intervalMs == 1000.0 })
        assertEquals("Press Up on each beat", ARROW_LAG_BLOCKS[0].prompt)
    }

    @Test
    fun cooldownCoversThreePatternsAtThreeTempos() {
        assertEquals(9, COOLDOWN_BLOCKS.size)
        assertEquals(listOf(500.0, 1000.0 / 3, 250.0),
            COOLDOWN_BLOCKS.filter { it.stage == Stage.COOLDOWN_REPEAT }.map { it.intervalMs })
        assertTrue(COOLDOWN_BLOCKS.all { it.beats == 8 })
    }

    @Test
    fun alternatingBlocksSwitchKeysEveryBeat() {
        val alt = COOLDOWN_BLOCKS.first { it.stage == Stage.COOLDOWN_ALTERNATE }
        assertEquals(RemoteKey.LEFT, alt.keyFor(0))
        assertEquals(RemoteKey.RIGHT, alt.keyFor(1))
        assertEquals(RemoteKey.LEFT, alt.keyFor(2))
    }

    @Test
    fun aRunSchedulesLeadInThenScoredBeats() {
        val run = BlockRun(OK_LAG_BLOCKS.single(), 5000.0)
        assertEquals(listOf(6000.0, 7000.0, 8000.0, 9000.0, 10000.0, 11000.0), run.allBeats)
        assertEquals(listOf(8000.0, 9000.0, 10000.0, 11000.0), run.beats)
        assertEquals(11500.0, run.endMs, 0.0)
    }

    @Test
    fun holdRunsLastABeatLonger() {
        val run = BlockRun(HOLD_BLOCKS.first(), 0.0)
        assertTrue(run.block.hold)
        assertEquals(7000.0, run.endMs, 0.0)
    }

    @Test
    fun onlyTheBlocksKeysAfterTheLeadInCount() {
        val run = BlockRun(ARROW_LAG_BLOCKS[1], 0.0) // Right; lead-in beats at 1000 and 2000
        run.down(RemoteKey.RIGHT, 2010.0) // a practice press on the last lead-in beat
        run.down(RemoteKey.LEFT, 3100.0) // the wrong key
        run.down(RemoteKey.RIGHT, 3100.0)
        run.up(RemoteKey.RIGHT, 3200.0)
        assertEquals(listOf(3100.0), run.presses)
        assertEquals(listOf(3200.0), run.releases)
        assertEquals(TempoRun(1000.0, run.beats, listOf(3100.0)), run.tempoRun())
    }

    @Test
    fun keyNamesReadWell() {
        assertEquals("Up", keyName(RemoteKey.UP))
        assertEquals("OK", keyName(RemoteKey.OK))
    }

    @Test
    fun clickIsA20msMonoWav() {
        val wav = clickWav()
        val samples = CLICK_RATE * 20 / 1000
        assertEquals(44 + samples * 2, wav.size)
        assertArrayEquals("RIFF".toByteArray(), wav.copyOfRange(0, 4))
        assertArrayEquals("WAVE".toByteArray(), wav.copyOfRange(8, 12))
        val header = ByteBuffer.wrap(wav).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(1, header.getShort(22).toInt()) // mono
        assertEquals(CLICK_RATE, header.getInt(24))
        assertEquals(samples * 2, header.getInt(40))
        assertFalse(wav.copyOfRange(44, wav.size).all { it == 0.toByte() })
    }
}
