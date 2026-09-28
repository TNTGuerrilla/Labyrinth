// Reads and writes Settings in SharedPreferences. Anything missing or invalid falls back
// to its default, like the desktop config file.
package com.bydesigninteractive.labyrinth

import android.content.Context
import com.bydesigninteractive.labyrinth.maze.Field
import com.bydesigninteractive.labyrinth.maze.Settings
import com.bydesigninteractive.labyrinth.maze.settingsFrom

object SettingsStore {
    private const val PREFS = "maze_settings"

    fun load(context: Context): Settings {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val raw = Field.entries.associateWith { field ->
            prefs.getString(field.name, null)?.toDoubleOrNull()
        }
        return settingsFrom(raw)
    }

    fun save(context: Context, settings: Settings) {
        val editor = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
        for (field in Field.entries) editor.putString(field.name, field.get(settings).toString())
        editor.apply()
    }
}
