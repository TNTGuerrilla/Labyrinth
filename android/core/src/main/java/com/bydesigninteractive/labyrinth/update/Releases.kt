// Picks the newest release of one Labyrinth product from the GitHub releases list. Pure logic, unit
// tested on the desktop JVM, and the same rules as the desktop updater.
package com.bydesigninteractive.labyrinth.update

import java.net.URI
import java.net.URISyntaxException
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

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
 * The highest [product] release newer than [current] whose asset has a published SHA-256.
 * Drafts, pre-releases and other products' tags are ignored; any malformed input gives null.
 */
fun newestRelease(json: String, current: String, product: Product): Release? {
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
        if (!tag.startsWith(product.tagPrefix)) continue
        val text = tag.removePrefix(product.tagPrefix)
        val version = parseVersion(text) ?: continue
        if (compareVersions(version, bestVersion) <= 0) continue
        val assets = release.optJSONArray("assets") ?: continue
        val asset = (0 until assets.length()).mapNotNull { assets.optJSONObject(it) }
            .firstOrNull { it.optString("name") == product.assetName } ?: continue
        val url = asset.optString("browser_download_url").takeIf { it.isNotEmpty() } ?: continue
        val sha = sha256Of(asset) ?: continue
        best = Release(text, url, sha)
        bestVersion = version
    }
    return best
}

private val GITHUB_HOSTS = setOf("github.com", "api.github.com")
// The local fake release server debug builds point at (see UPDATE_URL in build.gradle.kts).
private val FAKE_SERVER_HOSTS = setOf("10.0.2.2", "127.0.0.1", "localhost")

/**
 * Whether the updater may download from [url]: https from GitHub or its asset storage, and in
 * a debug build also plain http from the local fake release server. Anything else, such as a
 * file: URL, is refused before a connection is opened.
 */
fun isAllowedDownloadUrl(url: String, debug: Boolean): Boolean {
    val uri = try {
        URI(url)
    } catch (_: URISyntaxException) {
        return false
    }
    val scheme = uri.scheme?.lowercase() ?: return false
    val host = uri.host?.lowercase() ?: return false
    if (scheme == "https" && (host in GITHUB_HOSTS || host.endsWith(".githubusercontent.com"))) return true
    return debug && scheme == "http" && host in FAKE_SERVER_HOSTS
}

private fun sha256Of(asset: JSONObject): String? {
    val digest = asset.optString("digest")
    if (!digest.startsWith("sha256:")) return null
    return digest.removePrefix("sha256:").lowercase().takeIf { SHA256.matches(it) }
}
