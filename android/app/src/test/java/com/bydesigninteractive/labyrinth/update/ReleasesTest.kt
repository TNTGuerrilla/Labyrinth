package com.bydesigninteractive.labyrinth.update

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
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
        assertEquals(Release("1.10.0", "https://example.test/LabyrinthTV.apk", SHA), newestRelease(json, "1.0.0"))
        assertNull(newestRelease(json, "1.10.0"))
    }

    @Test
    fun skipsReleasesWithoutAVerifiableApk() {
        val json = list(
            release("labyrinth-tv-v1.5.0", asset("LabyrinthTV.apk", sha = null)),
            release("labyrinth-tv-v1.6.0", asset("LabyrinthTV.apk", sha = "zz")),
            release("labyrinth-tv-v1.7.0", asset("Other.apk")),
            release("labyrinth-tv-v1.4.0", asset("LabyrinthTV.apk", sha = "AB".repeat(32))),
        )
        assertEquals(Release("1.4.0", "https://example.test/LabyrinthTV.apk", SHA), newestRelease(json, "1.0.0"))
    }

    @Test
    fun junkIsIgnored() {
        assertNull(newestRelease("not json", "1.0.0"))
        assertNull(newestRelease("{}", "1.0.0"))
        assertNull(newestRelease("""[null, 3, {"tag_name": 5}, {"tag_name": "labyrinth-tv-v2.0.0", "assets": "x"}]""", "1.0.0"))
        assertNull(newestRelease(list(release("labyrinth-tv-v2.0.0", asset("LabyrinthTV.apk"))), "bad"))
    }
}
