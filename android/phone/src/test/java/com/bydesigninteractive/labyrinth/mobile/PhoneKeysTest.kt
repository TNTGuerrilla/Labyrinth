package com.bydesigninteractive.labyrinth.mobile

import android.view.KeyEvent
import com.bydesigninteractive.labyrinth.game.RemoteKey
import org.junit.Assert.assertEquals
import org.junit.Test

class PhoneKeysTest {
    @Test
    fun wasdSteers() {
        assertEquals(RemoteKey.UP, phoneKey(KeyEvent.KEYCODE_W))
        assertEquals(RemoteKey.LEFT, phoneKey(KeyEvent.KEYCODE_A))
        assertEquals(RemoteKey.DOWN, phoneKey(KeyEvent.KEYCODE_S))
        assertEquals(RemoteKey.RIGHT, phoneKey(KeyEvent.KEYCODE_D))
    }

    @Test
    fun remoteKeysStillWork() {
        assertEquals(RemoteKey.UP, phoneKey(KeyEvent.KEYCODE_DPAD_UP))
        assertEquals(RemoteKey.OK, phoneKey(KeyEvent.KEYCODE_BUTTON_A))
        assertEquals(RemoteKey.OK, phoneKey(KeyEvent.KEYCODE_ENTER))
        assertEquals(RemoteKey.BACK, phoneKey(KeyEvent.KEYCODE_BUTTON_B))
        assertEquals(RemoteKey.BACK, phoneKey(KeyEvent.KEYCODE_ESCAPE))
    }

    @Test
    fun startOpensTheMenuLikeOk() {
        assertEquals(RemoteKey.OK, phoneKey(KeyEvent.KEYCODE_BUTTON_START))
        assertEquals(RemoteKey.OK, phoneKey(KeyEvent.KEYCODE_MENU))
    }

    @Test
    fun shoulderButtonsAndPlusMinusZoom() {
        assertEquals(RemoteKey.VOLUME_UP, phoneKey(KeyEvent.KEYCODE_BUTTON_R1))
        assertEquals(RemoteKey.VOLUME_DOWN, phoneKey(KeyEvent.KEYCODE_BUTTON_L1))
        assertEquals(RemoteKey.VOLUME_UP, phoneKey(KeyEvent.KEYCODE_PLUS))
        assertEquals(RemoteKey.VOLUME_UP, phoneKey(KeyEvent.KEYCODE_EQUALS))
        assertEquals(RemoteKey.VOLUME_UP, phoneKey(KeyEvent.KEYCODE_NUMPAD_ADD))
        assertEquals(RemoteKey.VOLUME_DOWN, phoneKey(KeyEvent.KEYCODE_MINUS))
        assertEquals(RemoteKey.VOLUME_DOWN, phoneKey(KeyEvent.KEYCODE_NUMPAD_SUBTRACT))
    }

    @Test
    fun thePhonesVolumeKeysStayTheVolume() {
        assertEquals(RemoteKey.OTHER, phoneKey(KeyEvent.KEYCODE_VOLUME_UP))
        assertEquals(RemoteKey.OTHER, phoneKey(KeyEvent.KEYCODE_VOLUME_DOWN))
    }
}
