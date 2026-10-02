// Release notes: the part of a GitHub release body the app shows, collected across releases
// and stored as JSON. Pure logic, and the same rules as labyrinth_update/notes.py. The body's
// `---` line and everything after it (the SHA-256 line, install steps) stay on GitHub only.
package com.bydesigninteractive.labyrinth.update

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

const val RELEASES_TEXT = "github.com/TNTGuerrilla/Labyrinth/releases"
const val MORE_TEXT = "More at $RELEASES_TEXT"
const val BULLET = "- "
private const val CUTOFF = "---"
private const val MAX_ENTRIES = 20
private const val MAX_NOTES_CHARS = 20_000

data class NoteEntry(val version: String, val notes: String)

enum class LineKind { HEADING, TEXT, ITEM, BLANK }

data class NoteLine(val kind: LineKind, val text: String = "")

/** Everything before the first `---` line, without leading or trailing blank lines. */
fun extractNotes(body: String?): String {
    if (body == null) return ""
    val kept = ArrayList<String>()
    for (line in body.replace("\r\n", "\n").replace('\r', '\n').split('\n')) {
        if (line.trim() == CUTOFF) break
        kept.add(line.trimEnd())
    }
    while (kept.isNotEmpty() && kept.first().isBlank()) kept.removeAt(0)
    while (kept.isNotEmpty() && kept.last().isEmpty()) kept.removeAt(kept.size - 1)
    return kept.joinToString("\n")
}

private fun clean(text: String) = text.replace("**", "").replace("`", "").trim()

/** Headings (# removed), bullets (- or *), plain lines and single blank lines between them. */
fun parseNotes(text: String): List<NoteLine> {
    val lines = ArrayList<NoteLine>()
    for (raw in text.split('\n')) {
        val line = raw.trim()
        val (kind, body) = when {
            line.startsWith("#") -> LineKind.HEADING to line.trimStart('#')
            line.startsWith("- ") || line.startsWith("* ") -> LineKind.ITEM to line.substring(2)
            else -> LineKind.TEXT to line
        }
        val cleaned = clean(body)
        if (cleaned.isEmpty()) {
            if (lines.isNotEmpty() && lines.last().kind != LineKind.BLANK) lines.add(NoteLine(LineKind.BLANK))
            continue
        }
        lines.add(NoteLine(kind, cleaned))
    }
    while (lines.isNotEmpty() && lines.last().kind == LineKind.BLANK) lines.removeAt(lines.size - 1)
    return lines
}

private fun versionText(v: List<Int>) = v.joinToString(".")

private fun newestFirst(entries: Collection<Pair<List<Int>, NoteEntry>>) =
    entries.sortedWith { a, b -> compareVersions(b.first, a.first) }.map { it.second }.take(MAX_ENTRIES)

/** Notes of [product] releases above [current] up to and including [newest], newest first. */
fun collectNotes(json: String, current: String, newest: String, product: Product): List<NoteEntry> {
    val low = parseVersion(current) ?: return emptyList()
    val high = parseVersion(newest) ?: return emptyList()
    return notesIn(json, low, high, product)
}

/** The notes a start fetches (see [notesToFetch]), newest first. */
fun fetchedNotes(json: String, fetch: NotesFetch, product: Product): List<NoteEntry> {
    val high = parseVersion(fetch.version) ?: return emptyList()
    if (fetch.after == null) return notesIn(json, null, high, product).filter { parseVersion(it.version) == high }
    val low = parseVersion(fetch.after) ?: return emptyList()
    return notesIn(json, low, high, product)
}

/** Notes of [product] releases above [low] (no lower bound when null) up to and including [high]. */
private fun notesIn(json: String, low: List<Int>?, high: List<Int>, product: Product): List<NoteEntry> {
    val releases = try {
        JSONArray(json)
    } catch (_: JSONException) {
        return emptyList()
    }
    val found = HashMap<String, Pair<List<Int>, NoteEntry>>()
    for (i in 0 until releases.length()) {
        val release = releases.optJSONObject(i) ?: continue
        if (release.optBoolean("draft") || release.optBoolean("prerelease")) continue
        val tag = release.optString("tag_name")
        if (!tag.startsWith(product.tagPrefix)) continue
        val version = parseVersion(tag.removePrefix(product.tagPrefix)) ?: continue
        if ((low != null && compareVersions(version, low) <= 0) || compareVersions(version, high) > 0) continue
        // isNull first: Android's optString turns a JSON null into the text "null".
        val body = if (release.isNull("body")) null else release.optString("body")
        val notes = extractNotes(body).take(MAX_NOTES_CHARS)
        if (notes.isNotEmpty()) found[versionText(version)] = version to NoteEntry(versionText(version), notes)
    }
    return newestFirst(found.values)
}

/** After a check found a newer release: the fresh notes plus stored ones at or below [current]. */
fun mergeNotes(stored: List<NoteEntry>, fresh: List<NoteEntry>, current: String): List<NoteEntry> {
    val ours = parseVersion(current)
    val kept = HashMap<String, Pair<List<Int>, NoteEntry>>()
    for (entry in stored) {
        val v = parseVersion(entry.version) ?: continue
        if (ours != null && compareVersions(v, ours) <= 0) kept[versionText(v)] = v to entry
    }
    for (entry in fresh) {
        val v = parseVersion(entry.version) ?: continue
        kept[versionText(v)] = v to entry
    }
    return newestFirst(kept.values)
}

/** The stored form, read by every later version: [{"version": "1.3.0", "notes": "..."}]. */
fun notesToJson(entries: List<NoteEntry>): String = JSONArray().apply {
    entries.forEach { put(JSONObject().put("version", it.version).put("notes", it.notes)) }
}.toString()

fun notesFromJson(text: String?): List<NoteEntry> {
    if (text == null) return emptyList()
    val array = try {
        JSONArray(text)
    } catch (_: JSONException) {
        return emptyList()
    }
    return (0 until minOf(array.length(), MAX_ENTRIES)).mapNotNull { i ->
        val item = array.optJSONObject(i) ?: return@mapNotNull null
        val version = item.optString("version").takeIf { parseVersion(it) != null } ?: return@mapNotNull null
        val notes = item.opt("notes") as? String ?: return@mapNotNull null
        NoteEntry(version, notes)
    }
}
