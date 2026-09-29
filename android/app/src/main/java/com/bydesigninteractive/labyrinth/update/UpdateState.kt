// What the updater remembers between runs, and the rules for when to check and what to offer.
package com.bydesigninteractive.labyrinth.update

const val CHECK_INTERVAL_MS = 7L * 24 * 60 * 60 * 1000

data class UpdateState(val lastCheck: Long? = null, val found: Release? = null, val dismissed: String? = null)

/** Due on the first run, a week after the last check, or if the clock went back. */
fun isDue(state: UpdateState, nowMs: Long): Boolean {
    val last = state.lastCheck ?: return true
    val age = nowMs - last
    return age < 0 || age >= CHECK_INTERVAL_MS
}

/** The update notice earlier checks left pending: none while checks are off. */
fun pendingNotice(enabled: Boolean, state: UpdateState, current: String): Release? =
    if (enabled) visibleUpdate(state, current) else null

/** The release to offer: newer than the running version and not dismissed. */
fun visibleUpdate(state: UpdateState, current: String): Release? {
    val found = state.found ?: return null
    if (found.version == state.dismissed) return null
    val theirs = parseVersion(found.version) ?: return null
    val ours = parseVersion(current) ?: return null
    return found.takeIf { compareVersions(theirs, ours) > 0 }
}
