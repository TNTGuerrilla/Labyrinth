package com.bydesigninteractive.labyrinth.mobile

import android.view.KeyEvent
import com.bydesigninteractive.labyrinth.game.RemoteKey
import com.bydesigninteractive.labyrinth.play.remoteKey

/**
 * Android key codes as the phone game sees them: the TV remote's keys, plus WASD, a
 * controller's Start and shoulder buttons, and + and - for zoom. The phone's own volume keys
 * stay the volume. A controller's left stick arrives as D-pad keys (Android turns stick and
 * hat movement into D-pad key events when the app does not handle it).
 */
fun phoneKey(keyCode: Int): RemoteKey = when (keyCode) {
    KeyEvent.KEYCODE_W -> RemoteKey.UP
    KeyEvent.KEYCODE_A -> RemoteKey.LEFT
    KeyEvent.KEYCODE_S -> RemoteKey.DOWN
    KeyEvent.KEYCODE_D -> RemoteKey.RIGHT
    KeyEvent.KEYCODE_BUTTON_START, KeyEvent.KEYCODE_MENU -> RemoteKey.OK
    KeyEvent.KEYCODE_BUTTON_R1, KeyEvent.KEYCODE_PLUS, KeyEvent.KEYCODE_EQUALS, KeyEvent.KEYCODE_NUMPAD_ADD ->
        RemoteKey.VOLUME_UP
    KeyEvent.KEYCODE_BUTTON_L1, KeyEvent.KEYCODE_MINUS, KeyEvent.KEYCODE_NUMPAD_SUBTRACT -> RemoteKey.VOLUME_DOWN
    KeyEvent.KEYCODE_VOLUME_UP, KeyEvent.KEYCODE_VOLUME_DOWN -> RemoteKey.OTHER
    else -> remoteKey(keyCode)
}
