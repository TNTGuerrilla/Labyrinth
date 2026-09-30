// The phone's own settings and first-launch state in SharedPreferences, apart from the game
// settings in GameStore. Anything missing or invalid falls back to its default.
package com.bydesigninteractive.labyrinth.mobile

import android.content.Context

object PhoneStore {
    private const val PREFS = "phone_settings"
    private const val TOUCH = "touch"
    private const val HOLD = "hold"
    private const val HIDE_BARS = "hide_bars"
    private const val HAND = "hand"
    private const val CONTROLLER_USED = "controller_used"
    private const val HOW_TO_PLAY_SEEN = "how_to_play_seen"

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(context: Context): PhoneSettings {
        val p = prefs(context)
        return phoneSettingsFrom(
            p.getString(TOUCH, null),
            p.getString(HOLD, null),
            if (p.contains(HIDE_BARS)) p.getBoolean(HIDE_BARS, true) else null,
            p.getString(HAND, null),
        )
    }

    fun save(context: Context, s: PhoneSettings) {
        prefs(context).edit()
            .putString(TOUCH, s.touch.name)
            .putString(HOLD, s.hold.name)
            .putBoolean(HIDE_BARS, s.hideBars)
            .putString(HAND, s.hand.name)
            .apply()
    }

    fun controllerUsed(context: Context): Boolean = prefs(context).getBoolean(CONTROLLER_USED, false)

    fun markControllerUsed(context: Context) {
        prefs(context).edit().putBoolean(CONTROLLER_USED, true).apply()
    }

    fun howToPlaySeen(context: Context): Boolean = prefs(context).getBoolean(HOW_TO_PLAY_SEEN, false)

    fun markHowToPlaySeen(context: Context) {
        prefs(context).edit().putBoolean(HOW_TO_PLAY_SEEN, true).apply()
    }
}
