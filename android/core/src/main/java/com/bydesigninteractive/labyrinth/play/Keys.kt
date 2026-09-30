package com.bydesigninteractive.labyrinth.play

import android.view.KeyEvent
import com.bydesigninteractive.labyrinth.game.RemoteKey

/** Android key codes as the game sees them. OK covers the D-pad center and Enter keys. */
fun remoteKey(keyCode: Int): RemoteKey = when (keyCode) {
    KeyEvent.KEYCODE_DPAD_UP -> RemoteKey.UP
    KeyEvent.KEYCODE_DPAD_DOWN -> RemoteKey.DOWN
    KeyEvent.KEYCODE_DPAD_LEFT -> RemoteKey.LEFT
    KeyEvent.KEYCODE_DPAD_RIGHT -> RemoteKey.RIGHT
    KeyEvent.KEYCODE_DPAD_CENTER, KeyEvent.KEYCODE_ENTER, KeyEvent.KEYCODE_NUMPAD_ENTER,
    KeyEvent.KEYCODE_BUTTON_A -> RemoteKey.OK
    KeyEvent.KEYCODE_BACK, KeyEvent.KEYCODE_ESCAPE, KeyEvent.KEYCODE_BUTTON_B -> RemoteKey.BACK
    KeyEvent.KEYCODE_VOLUME_UP -> RemoteKey.VOLUME_UP
    KeyEvent.KEYCODE_VOLUME_DOWN -> RemoteKey.VOLUME_DOWN
    else -> RemoteKey.OTHER
}
