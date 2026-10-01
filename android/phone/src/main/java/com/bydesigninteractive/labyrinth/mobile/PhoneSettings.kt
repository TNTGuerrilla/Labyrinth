// Settings only the phone game has: how touch steers, how the phone may be held, and whether
// the system bars hide. The game's own settings are GameSettings, shared with the TV.
package com.bydesigninteractive.labyrinth.mobile

import com.bydesigninteractive.labyrinth.touch.Hold

/** The touch schemes, one active at a time. */
enum class TouchScheme(val label: String, val help: String) {
    SWIPE(
        "Swipe",
        "Swipe on the maze to run the dot to the next fork. Swipe again while it runs to choose the turn there.",
    ),
    DRAG(
        "Drag",
        "Trace the corridors with your finger: the dot follows the cells you draw through, and a wall stops the line. Drag back to erase. Let go and the dot finishes what you drew.",
    ),
    JOYSTICK(
        "Joystick",
        "Hold the joystick in the corner and slide your thumb around it to steer. Lift to let go.",
    ),
    TAP(
        "Tap to go",
        "Tap a cell: the dot walks there through places it has been, or down a corridor as far as its next fork.",
    ),
}

enum class Hand(val label: String) { LEFT("Left"), RIGHT("Right") }

data class PhoneSettings(
    val touch: TouchScheme = TouchScheme.SWIPE,
    val hold: Hold = Hold.AUTO,
    val hideBars: Boolean = true,
    val hand: Hand = Hand.RIGHT,
    val showTrace: Boolean = true,
)

/** PhoneSettings from stored values; anything missing or unknown keeps its default. */
fun phoneSettingsFrom(touch: String?, hold: String?, hideBars: Boolean?, hand: String? = null, showTrace: Boolean? = null): PhoneSettings {
    val d = PhoneSettings()
    return PhoneSettings(
        touch = TouchScheme.entries.firstOrNull { it.name == touch } ?: d.touch,
        hold = Hold.entries.firstOrNull { it.name == hold } ?: d.hold,
        hideBars = hideBars ?: d.hideBars,
        hand = Hand.entries.firstOrNull { it.name == hand } ?: d.hand,
        showTrace = showTrace ?: d.showTrace,
    )
}
