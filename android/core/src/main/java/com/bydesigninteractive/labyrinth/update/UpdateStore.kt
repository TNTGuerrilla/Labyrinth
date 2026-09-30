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

    /** Prefer [edit] for a read, change and write; use this directly only for the rare case
     * where the whole state is being replaced without reading it first. */
    fun save(context: Context, state: UpdateState) {
        prefs(context).edit().apply {
            if (state.lastCheck != null) putLong("last_check", state.lastCheck) else remove("last_check")
            putString("found_version", state.found?.version)
            putString("found_url", state.found?.url)
            putString("found_sha256", state.found?.sha256)
            putString("dismissed", state.dismissed)
        }.apply()
    }

    /**
     * Read, change and write UpdateState as one step. A check running on a background thread
     * and Dismiss on the main thread both write this state, and must not undo each other.
     */
    @Synchronized
    fun edit(context: Context, change: (UpdateState) -> UpdateState): UpdateState {
        val after = change(load(context))
        save(context, after)
        return after
    }

    fun enabled(context: Context): Boolean = prefs(context).getBoolean("check_updates", true)

    fun setEnabled(context: Context, value: Boolean) {
        prefs(context).edit().putBoolean("check_updates", value).apply()
    }

    private const val NOTES = "notes" // the JSON array of Notes.kt, a contract between versions
    private const val LAST_RUN = "last_run_version"
    private const val RUNS = "whats_new_runs"

    @Synchronized
    fun loadSeen(context: Context): SeenState {
        val p = prefs(context)
        return SeenState(
            lastRunVersion = p.getString(LAST_RUN, null)?.takeIf { parseVersion(it) != null },
            runs = p.getInt(RUNS, 0).coerceAtLeast(0),
            notes = notesFromJson(p.getString(NOTES, null)),
        )
    }

    @Synchronized
    fun saveSeen(context: Context, state: SeenState) {
        prefs(context).edit().apply {
            putString(NOTES, notesToJson(state.notes))
            putString(LAST_RUN, state.lastRunVersion)
            putInt(RUNS, state.runs)
        }.apply()
    }

    /**
     * Read, change and write the seen state as one step. The update check thread (notes) and
     * the main thread (seen, run count) both write it, and must not undo each other.
     */
    @Synchronized
    fun editSeen(context: Context, change: (SeenState) -> SeenState): SeenState {
        val before = loadSeen(context)
        val after = change(before)
        if (after != before) saveSeen(context, after)
        return after
    }

    /** Call once when the dream or the app starts: What's new to show now, or null. */
    fun startWhatsNew(context: Context, current: String): WhatsNew? {
        var shown: WhatsNew? = null
        editSeen(context) { state -> onStart(state, current).also { shown = it.second }.first }
        return shown
    }

    fun countWhatsNewRun(context: Context, current: String) { editSeen(context) { countRun(it, current) } }

    fun markWhatsNewSeen(context: Context, current: String) { editSeen(context) { markSeen(it, current) } }

    fun runningWhatsNew(context: Context, current: String): WhatsNew = runningNotes(loadSeen(context), current)
}
