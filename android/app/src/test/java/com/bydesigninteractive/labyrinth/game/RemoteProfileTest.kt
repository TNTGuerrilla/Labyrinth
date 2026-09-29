package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class RemoteProfileTest {
    @Test
    fun untestedRemoteAddsNothing() {
        val p = RemoteProfile()
        assertEquals(0.0, p.lagSeconds, 0.0)
        assertEquals(0.0, p.cooldownSeconds, 0.0)
        assertNull(p.holdGraceSeconds)
    }

    @Test
    fun cooldownIsTheLargerArrowValue() {
        assertEquals(0.12, RemoteProfile(arrowRepeatCooldownMs = 120, arrowAlternateCooldownMs = 80).cooldownSeconds, 1e-9)
    }

    @Test
    fun holdGraceIsTheGapPlus50CappedAt500() {
        assertEquals(0.15, RemoteProfile(arrowHoldGapMs = 100).holdGraceSeconds!!, 1e-9)
        assertEquals(0.5, RemoteProfile(arrowHoldGapMs = 480).holdGraceSeconds!!, 1e-9)
    }
}
