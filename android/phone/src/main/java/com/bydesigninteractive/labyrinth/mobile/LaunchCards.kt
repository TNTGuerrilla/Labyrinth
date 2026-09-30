// Which card a fresh launch shows before the first maze: at most one, the most important first.
// The others wait for a later launch (What's new stays pending; an update stays on offer).
package com.bydesigninteractive.labyrinth.mobile

enum class LaunchCard { HOW_TO_PLAY, WHATS_NEW, UPDATE }

fun launchCard(firstLaunch: Boolean, whatsNew: Boolean, update: Boolean): LaunchCard? = when {
    firstLaunch -> LaunchCard.HOW_TO_PLAY
    whatsNew -> LaunchCard.WHATS_NEW
    update -> LaunchCard.UPDATE
    else -> null
}
