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

/** The TV's card is this many times the Windows screensaver's. */
const val TV_CARD_SCALE = 1.25

/**
 * The section's fixed-size card, as maze_saver.whats_new.card_size: 540 x 690 scaled by the
 * screen's shorter side over 1440, then shrunk, aspect ratio kept, to fit 25% of the width
 * and 80% of the height. [scale] enlarges the card and its width limit alike (about 506 x 647
 * on a 1080p TV); the height limit stays 80%. Rounded half up.
 */
fun cardSize(w: Int, h: Int, scale: Double = TV_CARD_SCALE): Pair<Int, Int> {
    val s = minOf(w, h) / 1440.0 * scale
    val cw = 540 * s
    val ch = 690 * s
    val maxW = w * 0.25 * scale
    val maxH = h * 0.8
    val k = minOf(1.0, maxW / cw, maxH / ch)
    return minOf(Math.round(cw * k).toInt(), maxW.toInt()) to minOf(Math.round(ch * k).toInt(), maxH.toInt())
}

/**
 * Landscape: the card in a column on the right (card width plus a margin each side),
 * vertically centred; portrait: in a band at the bottom, horizontally centred. The board
 * keeps the rest, so the card never covers the maze.
 */
fun splitScreen(w: Int, h: Int, scale: Double = TV_CARD_SCALE): Split {
    val (cw, ch) = cardSize(w, h, scale)
    val margin = minOf(w, h) / 40
    if (w >= h) {
        val column = cw + 2 * margin
        return Split(Box(0, 0, w - column, h), Box(w - column + margin, (h - ch) / 2, cw, ch))
    }
    val band = ch + 2 * margin
    return Split(Box(0, 0, w, h - band), Box((w - cw) / 2, h - band + margin, cw, ch))
}
