package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ModeTest {
    @Test
    fun modesSayWhatIsOn() {
        assertTrue(Mode.BOTH.game && Mode.BOTH.screensaver)
        assertTrue(Mode.GAME.game)
        assertFalse(Mode.GAME.screensaver)
        assertFalse(Mode.SCREENSAVER.game)
    }

    @Test
    fun theCarouselWraps() {
        assertEquals(Mode.GAME, Mode.BOTH.next(1))
        assertEquals(Mode.BOTH, Mode.SCREENSAVER.next(1))
        assertEquals(Mode.SCREENSAVER, Mode.BOTH.next(-1))
    }

    @Test
    fun unknownNamesMeanBoth() {
        assertEquals(Mode.BOTH, modeFrom(null))
        assertEquals(Mode.BOTH, modeFrom("nonsense"))
        assertEquals(Mode.GAME, modeFrom("GAME"))
    }
}
