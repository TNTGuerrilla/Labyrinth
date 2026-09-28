// Keeps UpdateState and the "check for updates" switch in SharedPreferences.
package com.bydesigninteractive.labyrinth.update

import android.content.Context

object UpdateStore {
    private const val PREFS = "updates"

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    fun load(context: Context): UpdateState {
        val p = prefs(context)
        val version = p.getString("found_version", null)
        val url = p.getString("found_url", null)
        val sha = p.getString("found_sha256", null)
        val found = if (parseVersion(version) != null && url != null && sha != null) Release(version!!, url, sha) else null
        return UpdateState(
            lastCheck = if (p.contains("last_check")) p.getLong("last_check", 0) else null,
            found = found,
            dismissed = p.getString("dismissed", null)?.takeIf { parseVersion(it) != null },
        )
    }

    fun save(context: Context, state: UpdateState) {
        prefs(context).edit().apply {
            if (state.lastCheck != null) putLong("last_check", state.lastCheck) else remove("last_check")
            putString("found_version", state.found?.version)
            putString("found_url", state.found?.url)
            putString("found_sha256", state.found?.sha256)
            putString("dismissed", state.dismissed)
        }.apply()
    }

    fun enabled(context: Context): Boolean = prefs(context).getBoolean("check_updates", true)

    fun setEnabled(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean("check_updates", value).apply()
    }
}
