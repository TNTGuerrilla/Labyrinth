// After an update: when What's new shows, which notes, when it counts as seen, and the dream
// section's countdown, close rule and layout. Pure logic, the same rules as
// labyrinth_update/whats_new.py and maze_saver/whats_new.py.
package com.bydesigninteractive.labyrinth.update

const val SHOW_RUNS = 3
const val SHOW_MS = 60_000L
const val FADE_MS = 1_500L
const val CLOSES_IN = "Closes in "
const val CLOSES_AFTER = "Closes after this maze"

/** lastRunVersion: the version whose What's new was last seen (or the first that ran). */
data class SeenState(val lastRunVersion: String? = null, val runs: Int = 0, val notes: List<NoteEntry> = emptyList())

data class WhatsNew(val version: String, val entries: List<NoteEntry> = emptyList()) {
    fun lines(): List<NoteLine> {
        if (entries.isEmpty()) {
            return listOf(NoteLine(LineKind.TEXT, "Updated to version $version."), NoteLine(LineKind.TEXT, RELEASES_TEXT))
        }
        if (entries.size == 1) return parseNotes(entries[0].notes)
        val out = ArrayList<NoteLine>()
        for (entry in entries) {
            if (out.isNotEmpty()) out.add(NoteLine(LineKind.BLANK))
            out.add(NoteLine(LineKind.HEADING, "Version ${entry.version}"))
            out.addAll(parseNotes(entry.notes))
        }
        return out
    }
}

/** Entries above [low] (no lower bound when null) and at or below [high]. */
fun notesBetween(notes: List<NoteEntry>, low: String?, high: String): List<NoteEntry> {
    val top = parseVersion(high) ?: return emptyList()
    val bottom = low?.let { parseVersion(it) }
    return notes.filter { entry ->
        val v = parseVersion(entry.version)
        v != null && compareVersions(v, top) <= 0 && (bottom == null || compareVersions(v, bottom) > 0)
    }
}

fun isPending(state: SeenState, current: String): Boolean {
    val last = parseVersion(state.lastRunVersion) ?: return false
    val ours = parseVersion(current) ?: return false
    return compareVersions(last, ours) < 0
}

fun onStart(state: SeenState, current: String): Pair<SeenState, WhatsNew?> {
    if (parseVersion(current) == null) return state to null
    if (parseVersion(state.lastRunVersion) == null) return state.copy(lastRunVersion = current, runs = 0) to null
    if (isPending(state, current)) return state to WhatsNew(current, notesBetween(state.notes, state.lastRunVersion, current))
    return state to null
}

fun markSeen(state: SeenState, current: String): SeenState {
    if (!isPending(state, current)) return state
    val previous = parseVersion(state.lastRunVersion)!!
    val kept = state.notes.filter { e -> parseVersion(e.version)?.let { compareVersions(it, previous) > 0 } == true }
    return SeenState(current, 0, kept)
}

fun countRun(state: SeenState, current: String): SeenState {
    if (!isPending(state, current)) return state
    val runs = state.runs + 1
    return if (runs >= SHOW_RUNS) markSeen(state, current) else state.copy(runs = runs)
}

fun runningNotes(state: SeenState, current: String): WhatsNew =
    WhatsNew(current, notesBetween(state.notes, if (isPending(state, current)) state.lastRunVersion else null, current))

/** Whole seconds left, 60 down to 1, or null once the minute is over. */
fun countdownSeconds(elapsedMs: Long): Int? =
    if (elapsedMs >= SHOW_MS) null else (SHOW_MS / 1000 - maxOf(0L, elapsedMs) / 1000).toInt()

/** The minute counts from when the section appeared; the first solve after it closes the section. */
class SectionClock(val startedMs: Long) {
    var closedAtMs: Long? = null
        private set

    /** The board finished a maze. True when this solve closes the section. */
    fun boardSolved(nowMs: Long): Boolean {
        if (closedAtMs != null || nowMs - startedMs < SHOW_MS) return false
        closedAtMs = nowMs
        return true
    }
}

data class Box(val x: Int, val y: Int, val w: Int, val h: Int) {
    val right: Int get() = x + w
    val bottom: Int get() = y + h
}

data class Split(val board: Box, val section: Box)

/** Landscape: a strip on the right, 30% of the width; portrait: at the bottom, 30% of the height. */
fun splitScreen(w: Int, h: Int): Split {
    val marginX = w / 40
    val marginY = h / 20
    if (w >= h) {
        val strip = w * 3 / 10
        return Split(Box(0, 0, w - strip, h), Box(w - strip, marginY, strip - marginX, h - 2 * marginY))
    }
    val strip = h * 3 / 10
    return Split(Box(0, 0, w, h - strip), Box(marginX, h - strip, w - 2 * marginX, strip - marginY))
}
