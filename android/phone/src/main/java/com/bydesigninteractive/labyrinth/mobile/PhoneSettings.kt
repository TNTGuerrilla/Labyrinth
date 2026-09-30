// Settings only the phone game has: how touch steers, how the phone may be held, and whether
// the system bars hide. The game's own settings are GameSettings, shared with the TV.
package com.bydesigninteractive.labyrinth.mobile

import com.bydesigninteractive.labyrinth.touch.Hold

/** The touch schemes, one active at a time. Plan 4 adds Drag, Joystick and Tap to go. */
enum class TouchScheme(val label: String, val help: String) {
    SWIPE(
        "Swipe",
        "Swipe on the maze to run the dot to the next fork. Swipe again while it runs to choose the turn there.",
    ),
}

data class PhoneSettings(
    val touch: TouchScheme = TouchScheme.SWIPE,
    val hold: Hold = Hold.AUTO,
    val hideBars: Boolean = true,
)

/** PhoneSettings from stored values; anything missing or unknown keeps its default. */
fun phoneSettingsFrom(touch: String?, hold: String?, hideBars: Boolean?): PhoneSettings {
    val d = PhoneSettings()
    return PhoneSettings(
        touch = TouchScheme.entries.firstOrNull { it.name == touch } ?: d.touch,
        hold = Hold.entries.firstOrNull { it.name == hold } ?: d.hold,
        hideBars = hideBars ?: d.hideBars,
    )
}
