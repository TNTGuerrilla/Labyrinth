package com.bydesigninteractive.labyrinth.update

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Test

private fun release(tag: String, body: String?, draft: Boolean = false, prerelease: Boolean = false) =
    JSONObject().put("tag_name", tag).put("draft", draft).put("prerelease", prerelease)
        .put("body", body ?: JSONObject.NULL).put("assets", JSONArray())

private fun listing(vararg releases: JSONObject) = JSONArray().apply { releases.forEach { put(it) } }.toString()

class NotesTest {
    @Test
    fun cutsAtTheRuleAndTrims() {
        val body = "\r\n\r\n## Changes\r\n- **Faster** mazes\r\n* Fixed `x`\r\n\r\n\r\nThanks!\r\n\r\n---\r\nSHA-256: abc\r\n"
        assertEquals("## Changes\n- **Faster** mazes\n* Fixed `x`\n\n\nThanks!", extractNotes(body))
        assertEquals("a\n--- not a rule\nb", extractNotes("a\n--- not a rule\nb\n"))
        for (empty in listOf(null, "", "\n\n", "---\nonly the tail")) assertEquals("", extractNotes(empty))
    }

    @Test
    fun parsesHeadingsBulletsAndText() {
        assertEquals(
            listOf(
                NoteLine(LineKind.HEADING, "Changes"), NoteLine(LineKind.ITEM, "Faster mazes"),
                NoteLine(LineKind.ITEM, "Fixed x"), NoteLine(LineKind.BLANK), NoteLine(LineKind.TEXT, "Thanks!"),
            ),
            parseNotes("## Changes\n- **Faster** mazes\n* Fixed `x`\n\n\nThanks!"),
        )
    }

    @Test
    fun collectsNewerTvNotesNewestFirst() {
        val json = listing(
            release("labyrinth-tv-v1.4.0", "Four"), release("labyrinth-tv-v1.3.0", "Three\n---\nsha"),
            release("labyrinth-tv-v1.2.1", ""), release("labyrinth-tv-v1.2.0", "Two"),
            release("labyrinth-tv-v1.1.0", "One"), release("labyrinth-tv-v1.3.5", "d", draft = true),
            release("labyrinth-tv-v1.3.6", "p", prerelease = true), release("labyrinth-v1.3.0", "game"),
            release("labyrinth-tv-v1.2.2", null),
        )
        assertEquals(listOf(NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two")), collectNotes(json, "1.1.0", "1.3.0"))
        assertEquals(emptyList<NoteEntry>(), collectNotes("junk", "1.0.0", "2.0.0"))
    }

    @Test
    fun ordersNumerically() {
        val json = listing(release("labyrinth-tv-v1.9.0", "Nine"), release("labyrinth-tv-v1.10.0", "Ten"))
        assertEquals(listOf("1.10.0", "1.9.0"), collectNotes(json, "1.0.0", "1.10.0").map { it.version })
    }

    @Test
    fun mergeKeepsUnshownNotesAndAddsNewOnes() {
        val stored = listOf(NoteEntry("1.2.0", "Two"), NoteEntry("1.1.0", "One"), NoteEntry("1.5.0", "Pulled"))
        val fresh = listOf(NoteEntry("1.4.0", "Four"), NoteEntry("1.3.0", "Three"))
        assertEquals(
            listOf(NoteEntry("1.4.0", "Four"), NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two"), NoteEntry("1.1.0", "One")),
            mergeNotes(stored, fresh, "1.2.0"),
        )
    }

    @Test
    fun storedFormRoundTripsAndIgnoresJunk() {
        val entries = listOf(NoteEntry("1.3.0", "Three"), NoteEntry("1.2.0", "Two"))
        val json = notesToJson(entries)
        val first = JSONArray(json).getJSONObject(0)
        assertEquals("1.3.0", first.getString("version"))
        assertEquals("Three", first.getString("notes"))
        assertEquals(entries, notesFromJson(json))
        assertEquals(
            listOf(NoteEntry("1.1.0", "ok")),
            notesFromJson("""[{"version":"x","notes":"a"},{"version":"1.2.0"},5,{"version":"1.1.0","notes":"ok"}]"""),
        )
        assertEquals(emptyList<NoteEntry>(), notesFromJson(null))
        assertEquals(emptyList<NoteEntry>(), notesFromJson("nope"))
    }
}
