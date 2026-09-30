package com.bydesigninteractive.labyrinth.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private val SHA = "ab".repeat(32)

private fun asset(name: String, sha: String? = SHA): String {
    val digest = if (sha != null) ""","digest":"sha256:$sha"""" else ""
    return """{"name":"$name","browser_download_url":"https://example.test/$name"$digest}"""
}

private fun release(tag: String, vararg assets: String, draft: Boolean = false, pre: Boolean = false) =
    """{"tag_name":"$tag","draft":$draft,"prerelease":$pre,"assets":[${assets.joinToString(",")}]}"""

private fun list(vararg releases: String) = "[${releases.joinToString(",")}]"

class ReleasesTest {
    @Test
    fun parsesVersions() {
        assertEquals(listOf(1, 2, 3), parseVersion("1.2.3"))
        assertEquals(listOf(10, 0, 12), parseVersion(" 10.0.12 "))
        for (bad in listOf("1.2", "1.2.3.4", "v1.2.3", "", null, "99999999999.0.0")) assertNull(parseVersion(bad))
    }

    @Test
    fun picksTheNewestTvRelease() {
        val json = list(
            release("labyrinth-tv-v1.1.0", asset("LabyrinthTV.apk")),
            release("labyrinth-tv-v1.10.0", asset("LabyrinthTV.apk")),
            release("labyrinth-tv-v1.9.0", asset("LabyrinthTV.apk")),
            release("labyrinth-v5.0.0", asset("Labyrinth.exe")),
            release("labyrinth-tv-v2.0.0", asset("LabyrinthTV.apk"), draft = true),
            release("labyrinth-tv-v3.0.0", asset("LabyrinthTV.apk"), pre = true),
        )
        assertEquals(Release("1.10.0", "https://example.test/LabyrinthTV.apk", SHA), newestRelease(json, "1.0.0", TV_PRODUCT))
        assertNull(newestRelease(json, "1.10.0", TV_PRODUCT))
    }

    @Test
    fun skipsReleasesWithoutAVerifiableApk() {
        val json = list(
            release("labyrinth-tv-v1.5.0", asset("LabyrinthTV.apk", sha = null)),
            release("labyrinth-tv-v1.6.0", asset("LabyrinthTV.apk", sha = "zz")),
            release("labyrinth-tv-v1.7.0", asset("Other.apk")),
            release("labyrinth-tv-v1.4.0", asset("LabyrinthTV.apk", sha = "AB".repeat(32))),
        )
        assertEquals(Release("1.4.0", "https://example.test/LabyrinthTV.apk", SHA), newestRelease(json, "1.0.0", TV_PRODUCT))
    }

    @Test
    fun downloadsComeOnlyFromGithubOverHttps() {
        for (good in listOf(
            "https://github.com/TNTGuerrilla/Labyrinth/releases/download/labyrinth-tv-v1.2.0/LabyrinthTV.apk",
            "https://api.github.com/repos/TNTGuerrilla/Labyrinth/releases/assets/1",
            "https://objects.githubusercontent.com/x/LabyrinthTV.apk",
            "https://release-assets.githubusercontent.com/x",
            "HTTPS://GitHub.com/x",
        )) assertTrue(good, isAllowedDownloadUrl(good, debug = false))
        for (bad in listOf(
            "http://github.com/x",
            "file:///sdcard/LabyrinthTV.apk",
            "content://evil/LabyrinthTV.apk",
            "ftp://github.com/x",
            "https://example.test/LabyrinthTV.apk",
            "https://github.com.evil.test/x",
            "https://evilgithub.com/x",
            "https://githubusercontent.com.evil.test/x",
            "https://evilgithubusercontent.com/x",
            "https://github.com@evil.test/x",
            "http://10.0.2.2:8765/LabyrinthTV.apk",
            "not a url",
            "",
        )) assertFalse(bad, isAllowedDownloadUrl(bad, debug = false))
    }

    @Test
    fun debugBuildsAlsoAcceptTheLocalFakeServer() {
        for (local in listOf("http://10.0.2.2:8765/LabyrinthTV.apk", "http://127.0.0.1:8765/a", "http://localhost:8765/a")) {
            assertTrue(local, isAllowedDownloadUrl(local, debug = true))
            assertFalse(local, isAllowedDownloadUrl(local, debug = false))
        }
        assertTrue(isAllowedDownloadUrl("https://github.com/x", debug = true))
        assertFalse(isAllowedDownloadUrl("http://192.168.1.5:8765/a", debug = true))
        assertFalse(isAllowedDownloadUrl("file:///data/local/tmp/a.apk", debug = true))
    }

    @Test
    fun junkIsIgnored() {
        assertNull(newestRelease("not json", "1.0.0", TV_PRODUCT))
        assertNull(newestRelease("{}", "1.0.0", TV_PRODUCT))
        assertNull(newestRelease("""[null, 3, {"tag_name": 5}, {"tag_name": "labyrinth-tv-v2.0.0", "assets": "x"}]""", "1.0.0", TV_PRODUCT))
        assertNull(newestRelease(list(release("labyrinth-tv-v2.0.0", asset("LabyrinthTV.apk"))), "bad", TV_PRODUCT))
    }
}
