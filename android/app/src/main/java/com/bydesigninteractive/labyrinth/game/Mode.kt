// Which parts of the app are on: chosen on the settings screen with left and right.
package com.bydesigninteractive.labyrinth.game

enum class Mode(val label: String, val game: Boolean, val screensaver: Boolean) {
    BOTH("Both", true, true),
    GAME("Game", true, false),
    SCREENSAVER("Screensaver", false, true);

    fun next(sign: Int): Mode = entries[(ordinal + sign + entries.size) % entries.size]
}

fun modeFrom(name: String?): Mode = Mode.entries.firstOrNull { it.name == name } ?: Mode.BOTH
