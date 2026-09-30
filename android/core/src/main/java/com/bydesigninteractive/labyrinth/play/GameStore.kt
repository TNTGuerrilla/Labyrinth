// Game settings, the remote test result and the app mode in SharedPreferences, kept apart
// from the screensaver's settings so neither affects the other. Anything missing or
// invalid falls back to its default.
package com.bydesigninteractive.labyrinth.play

import android.content.Context
import com.bydesigninteractive.labyrinth.game.GameField
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.Mode
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.game.gameSettingsFrom
import com.bydesigninteractive.labyrinth.game.modeFrom

object GameStore {
    private const val SETTINGS = "game_settings"
    private const val REMOTE = "remote_profile"
    private const val APP = "app"
    private const val MODE = "mode"

    fun load(context: Context): GameSettings {
        val prefs = context.getSharedPreferences(SETTINGS, Context.MODE_PRIVATE)
        return gameSettingsFrom(GameField.entries.associateWith { prefs.getString(it.name, null)?.toDoubleOrNull() })
    }

    fun save(context: Context, s: GameSettings) {
        val editor = context.getSharedPreferences(SETTINGS, Context.MODE_PRIVATE).edit()
        for (field in GameField.entries) editor.putString(field.name, field.get(s).toString())
        editor.apply()
    }

    /** The stored remote test result, or null if the test has never been completed. */
    fun loadRemote(context: Context): RemoteProfile? {
        val p = context.getSharedPreferences(REMOTE, Context.MODE_PRIVATE)
        if (!p.contains("testedAtMillis")) return null
        fun gap(key: String) = p.getInt(key, -1).takeIf { it >= 0 }
        return RemoteProfile(
            arrowLagMs = p.getInt("arrowLagMs", 0),
            okLagMs = p.getInt("okLagMs", 0),
            soundDelayMs = p.getInt("soundDelayMs", 0),
            arrowRepeatCooldownMs = p.getInt("arrowRepeatCooldownMs", 0),
            arrowAlternateCooldownMs = p.getInt("arrowAlternateCooldownMs", 0),
            okCooldownMs = p.getInt("okCooldownMs", 0),
            arrowHoldGapMs = gap("arrowHoldGapMs"),
            okHoldGapMs = gap("okHoldGapMs"),
            testedAtMillis = p.getLong("testedAtMillis", 0),
        )
    }

    fun saveRemote(context: Context, r: RemoteProfile) {
        context.getSharedPreferences(REMOTE, Context.MODE_PRIVATE).edit()
            .putInt("arrowLagMs", r.arrowLagMs)
            .putInt("okLagMs", r.okLagMs)
            .putInt("soundDelayMs", r.soundDelayMs)
            .putInt("arrowRepeatCooldownMs", r.arrowRepeatCooldownMs)
            .putInt("arrowAlternateCooldownMs", r.arrowAlternateCooldownMs)
            .putInt("okCooldownMs", r.okCooldownMs)
            .putInt("arrowHoldGapMs", r.arrowHoldGapMs ?: -1)
            .putInt("okHoldGapMs", r.okHoldGapMs ?: -1)
            .putLong("testedAtMillis", r.testedAtMillis)
            .apply()
    }

    fun mode(context: Context): Mode =
        modeFrom(context.getSharedPreferences(APP, Context.MODE_PRIVATE).getString(MODE, null))

    fun setMode(context: Context, m: Mode) {
        context.getSharedPreferences(APP, Context.MODE_PRIVATE).edit().putString(MODE, m.name).apply()
    }
}

/** Per-process state: a session starts when the app is opened from the TV's home screen. */
object Session {
    /** The first game of a session opens with the Controls tab showing. */
    var controlsShown = false
}
