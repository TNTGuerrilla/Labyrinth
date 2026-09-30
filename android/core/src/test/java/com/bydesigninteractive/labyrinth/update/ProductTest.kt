package com.bydesigninteractive.labyrinth.update

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

private val SHA = "cd".repeat(32)

private fun release(tag: String, asset: String, body: String = "Notes for $tag") =
    JSONObject().put("tag_name", tag).put("draft", false).put("prerelease", false).put("body", body)
        .put("assets", JSONArray().put(
            JSONObject().put("name", asset).put("browser_download_url", "https://example.test/$asset")
                .put("digest", "sha256:$SHA"),
        ))

private fun listing(vararg releases: JSONObject) = JSONArray().apply { releases.forEach { put(it) } }.toString()

class ProductTest {
    // These values are contracts with every installed copy: never change them.
    @Test
    fun productsKeepTheirPublishedNames() {
        assertEquals(Product("labyrinth-tv-v", "LabyrinthTV.apk", "Labyrinth-TV-updater"), TV_PRODUCT)
        assertEquals(Product("labyrinth-mobile-v", "LabyrinthMobile.apk", "Labyrinth-Mobile-updater"), MOBILE_PRODUCT)
    }

    @Test
    fun eachProductSeesOnlyItsOwnReleases() {
        val json = listing(
            release("labyrinth-tv-v1.4.0", "LabyrinthTV.apk"),
            release("labyrinth-mobile-v1.1.0", "LabyrinthMobile.apk"),
            release("labyrinth-v1.5.0", "Labyrinth.exe"),
        )
        assertEquals(Release("1.4.0", "https://example.test/LabyrinthTV.apk", SHA), newestRelease(json, "1.0.0", TV_PRODUCT))
        assertEquals(
            Release("1.1.0", "https://example.test/LabyrinthMobile.apk", SHA),
            newestRelease(json, "1.0.0", MOBILE_PRODUCT),
        )
    }

    @Test
    fun aMobileTagWithTheTvAssetIsNotAMobileRelease() {
        val json = listing(release("labyrinth-mobile-v1.1.0", "LabyrinthTV.apk"))
        assertNull(newestRelease(json, "1.0.0", MOBILE_PRODUCT))
    }

    @Test
    fun notesComeOnlyFromTheProductsOwnReleases() {
        val json = listing(
            release("labyrinth-tv-v1.2.0", "LabyrinthTV.apk", "TV two"),
            release("labyrinth-mobile-v1.2.0", "LabyrinthMobile.apk", "Mobile two"),
        )
        assertEquals(listOf(NoteEntry("1.2.0", "Mobile two")), collectNotes(json, "1.0.0", "1.2.0", MOBILE_PRODUCT))
        assertEquals(listOf(NoteEntry("1.2.0", "TV two")), collectNotes(json, "1.0.0", "1.2.0", TV_PRODUCT))
    }
}
