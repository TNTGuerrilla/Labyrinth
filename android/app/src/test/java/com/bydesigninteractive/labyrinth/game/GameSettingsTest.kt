package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class GameSettingsTest {
    @Test
    fun defaultsMatchTheDesktop() {
        val s = GameSettings()
        assertEquals(5.0, s.glideSpeed, 0.0)
        assertEquals(0.2, s.turnPause, 0.0)
        assertEquals("medium", s.size)
        assertEquals(0, s.zoomSteps)
    }

    @Test
    fun everyDefaultIsValid() {
        val s = GameSettings()
        for (f in GameField.entries) assertEquals(f.get(s), f.validate(f.get(s)))
    }

    @Test
    fun badValuesKeepTheirDefaults() {
        val raw = mapOf(
            GameField.GLIDE_SPEED to 99.0, GameField.MAX_LEADS to 3.5, GameField.FOLLOW_BENDS to 2.0,
            GameField.SIZE to 7.0, GameField.CUSTOM_MAX to 201.0, GameField.TURN_PAUSE to null,
        )
        assertEquals(GameSettings(), gameSettingsFrom(raw))
    }

    @Test
    fun goodValuesAreRead() {
        val s = gameSettingsFrom(mapOf(GameField.GLIDE_SPEED to 12.0, GameField.FOLLOW_BENDS to 0.0, GameField.SIZE to 3.0))
        assertEquals(12.0, s.glideSpeed, 0.0)
        assertFalse(s.followBends)
        assertEquals("xl", s.size)
    }

    @Test
    fun adjustStepsCleanly() {
        val s = adjust(GameSettings(), GameField.TURN_PAUSE, 1, 0)
        assertEquals(0.25, s.turnPause, 0.0)
        assertEquals("0.25", GameField.TURN_PAUSE.format(s.turnPause))
    }

    @Test
    fun adjustClampsAndSpeedsUpWhenHeld() {
        assertEquals(40.0, adjust(GameSettings(glideSpeed = 39.0), GameField.GLIDE_SPEED, 1, 0).glideSpeed, 0.0)
        assertEquals(40.0, adjust(GameSettings(glideSpeed = 39.0), GameField.GLIDE_SPEED, 1, 30).glideSpeed, 0.0)
        assertEquals(10.0, adjust(GameSettings(glideSpeed = 5.0), GameField.GLIDE_SPEED, 1, 8).glideSpeed, 0.0)
        assertEquals(15.0, adjust(GameSettings(glideSpeed = 5.0), GameField.GLIDE_SPEED, 1, 20).glideSpeed, 0.0)
    }

    @Test
    fun sizeChoiceClampsAtTheEnds() {
        assertEquals("custom", adjust(GameSettings(size = "custom"), GameField.SIZE, 1, 0).size)
        assertEquals("small", adjust(GameSettings(size = "small"), GameField.SIZE, -1, 0).size)
        assertEquals("large", adjust(GameSettings(size = "medium"), GameField.SIZE, 1, 0).size)
    }

    @Test
    fun customBoundsPushEachOther() {
        val s = adjust(GameSettings(customMin = 40, customMax = 40), GameField.CUSTOM_MIN, 1, 0)
        assertEquals(41, s.customMin)
        assertEquals(41, s.customMax)
        val t = adjust(GameSettings(customMin = 40, customMax = 40), GameField.CUSTOM_MAX, -1, 0)
        assertEquals(39, t.customMin)
        assertEquals(39, t.customMax)
    }

    @Test
    fun toggleFlipsOnlyToggles() {
        assertFalse(toggle(GameSettings(), GameField.FOLLOW_BENDS).followBends)
        assertEquals(GameSettings(), toggle(GameSettings(), GameField.GLIDE_SPEED))
    }

    @Test
    fun formats() {
        assertEquals("On", GameField.MULTICOLOR.format(1.0))
        assertEquals("Off", GameField.MULTICOLOR.format(0.0))
        assertEquals("5", GameField.GLIDE_SPEED.format(5.0))
        assertEquals("Medium", GameField.SIZE.format(1.0))
        assertEquals("100%", GameField.ZOOM.format(0.0))
        assertEquals("195%", GameField.ZOOM.format(3.0))
        assertNull(GameField.ZOOM.validate(13.0))
    }
}
