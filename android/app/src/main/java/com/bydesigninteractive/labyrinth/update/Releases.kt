// Picks the newest Labyrinth TV release from the GitHub releases list. Pure logic, unit
// tested on the desktop JVM, and the same rules as the desktop updater.
package com.bydesigninteractive.labyrinth.update

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

const val TAG_PREFIX = "labyrinth-tv-v"
const val ASSET_NAME = "LabyrinthTV.apk"
private val VERSION = Regex("""(\d+)\.(\d+)\.(\d+)""")
private val SHA256 = Regex("[0-9a-f]{64}")

data class Release(val version: String, val url: String, val sha256: String)

/** [major, minor, patch] for "X.Y.Z", or null. */
fun parseVersion(text: String?): List<Int>? {
    val match = text?.trim()?.let { VERSION.matchEntire(it) } ?: return null
    val parts = match.groupValues.drop(1).map { it.toIntOrNull() }
    return if (parts.all { it != null }) parts.map { it!! } else null
}

fun compareVersions(a: List<Int>, b: List<Int>): Int {
    for (i in 0 until 3) {
        val c = a[i].compareTo(b[i])
        if (c != 0) return c
    }
    return 0
}

/**
 * The highest TV release newer than [current] whose APK has a published SHA-256. Drafts,
 * pre-releases and other products' tags are ignored; any malformed input gives null.
 */
fun newestRelease(json: String, current: String): Release? {
    var bestVersion = parseVersion(current) ?: return null
    val releases = try {
        JSONArray(json)
    } catch (_: JSONException) {
        return null
    }
    var best: Release? = null
    for (i in 0 until releases.length()) {
        val release = releases.optJSONObject(i) ?: continue
        if (release.optBoolean("draft") || release.optBoolean("prerelease")) continue
        val tag = release.optString("tag_name")
        if (!tag.startsWith(TAG_PREFIX)) continue
        val text = tag.removePrefix(TAG_PREFIX)
        val version = parseVersion(text) ?: continue
        if (compareVersions(version, bestVersion) <= 0) continue
        val assets = release.optJSONArray("assets") ?: continue
        val asset = (0 until assets.length()).mapNotNull { assets.optJSONObject(it) }
            .firstOrNull { it.optString("name") == ASSET_NAME } ?: continue
        val url = asset.optString("browser_download_url").takeIf { it.isNotEmpty() } ?: continue
        val sha = sha256Of(asset) ?: continue
        best = Release(text, url, sha)
        bestVersion = version
    }
    return best
}

private fun sha256Of(asset: JSONObject): String? {
    val digest = asset.optString("digest")
    if (!digest.startsWith("sha256:")) return null
    return digest.removePrefix("sha256:").lowercase().takeIf { SHA256.matches(it) }
}
