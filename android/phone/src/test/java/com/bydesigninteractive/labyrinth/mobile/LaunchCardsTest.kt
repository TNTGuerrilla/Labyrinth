package com.bydesigninteractive.labyrinth.mobile

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class LaunchCardsTest {
    @Test
    fun atMostOneCardInPriorityOrder() {
        assertEquals(LaunchCard.HOW_TO_PLAY, launchCard(firstLaunch = true, whatsNew = true, update = true))
        assertEquals(LaunchCard.WHATS_NEW, launchCard(firstLaunch = false, whatsNew = true, update = true))
        assertEquals(LaunchCard.UPDATE, launchCard(firstLaunch = false, whatsNew = false, update = true))
        assertNull(launchCard(firstLaunch = false, whatsNew = false, update = false))
    }
}
