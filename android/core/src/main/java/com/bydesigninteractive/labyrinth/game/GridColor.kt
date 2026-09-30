// The game's grid line color, as packed ARGB (the same value as Color.rgb, without android.graphics).
package com.bydesigninteractive.labyrinth.game

private const val FULL_R = 150
private const val FULL_G = 160
private const val FULL_B = 200

/** Each channel of (150, 160, 200) times strength percent, rounded down; 20 gives (30, 32, 40). */
fun gridColor(strength: Int): Int =
    (0xFF shl 24) or (FULL_R * strength / 100 shl 16) or (FULL_G * strength / 100 shl 8) or (FULL_B * strength / 100)
