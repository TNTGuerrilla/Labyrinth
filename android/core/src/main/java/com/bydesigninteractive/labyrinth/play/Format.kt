package com.bydesigninteractive.labyrinth.play

/** A timer reading as M:SS. */
fun formatTime(seconds: Double): String {
    val s = seconds.toInt()
    return "%d:%02d".format(s / 60, s % 60)
}
