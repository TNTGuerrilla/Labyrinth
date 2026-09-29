// The remote test's beats: which blocks each step runs, when their beats fall, and the
// key times recorded during them. Beats are milliseconds on the same clock as the key
// events (Android's uptime clock); the activity schedules clicks and drawing from them.
package com.bydesigninteractive.labyrinth.game

enum class Stage { ARROW_LAG, OK_LAG, COOLDOWN_REPEAT, COOLDOWN_ALTERNATE, COOLDOWN_OK, HOLD_ARROW, HOLD_OK }

data class Block(
    val stage: Stage,
    val keys: List<RemoteKey>,
    val intervalMs: Double,
    /** Practice beats before the scored ones. */
    val leadIn: Int,
    val beats: Int,
    val prompt: String,
) {
    /** The key a beat asks for; alternating blocks switch every beat, lead-in included. */
    fun keyFor(beat: Int): RemoteKey = keys[beat % keys.size]

    val hold: Boolean get() = stage == Stage.HOLD_ARROW || stage == Stage.HOLD_OK
}

fun keyName(k: RemoteKey): String = when (k) {
    RemoteKey.UP -> "Up"
    RemoteKey.DOWN -> "Down"
    RemoteKey.LEFT -> "Left"
    RemoteKey.RIGHT -> "Right"
    RemoteKey.OK -> "OK"
    else -> k.name
}

val ARROW_LAG_BLOCKS = listOf(RemoteKey.UP, RemoteKey.RIGHT, RemoteKey.DOWN, RemoteKey.LEFT).map {
    Block(Stage.ARROW_LAG, listOf(it), 1000.0, 2, 4, "Press ${keyName(it)} on each beat")
}

val OK_LAG_BLOCKS = listOf(Block(Stage.OK_LAG, listOf(RemoteKey.OK), 1000.0, 2, 4, "Press OK on each beat"))

private val COOLDOWN_TEMPOS = listOf(2, 3, 4)

val COOLDOWN_BLOCKS = listOf(
    Triple(Stage.COOLDOWN_REPEAT, listOf(RemoteKey.RIGHT), "Press Right on every beat"),
    Triple(Stage.COOLDOWN_ALTERNATE, listOf(RemoteKey.LEFT, RemoteKey.RIGHT), "Press Left and Right in turn, one per beat"),
    Triple(Stage.COOLDOWN_OK, listOf(RemoteKey.OK), "Press OK on every beat"),
).flatMap { (stage, keys, prompt) ->
    COOLDOWN_TEMPOS.map { Block(stage, keys, 1000.0 / it, 4, 8, "$prompt ($it per second)") }
}

val HOLD_BLOCKS = listOf(
    Block(Stage.HOLD_ARROW, listOf(RemoteKey.RIGHT), 1000.0, 2, 4, "Hold Right from the first beat and let go on the fourth"),
    Block(Stage.HOLD_OK, listOf(RemoteKey.OK), 1000.0, 2, 4, "Hold OK from the first beat and let go on the fourth"),
)

class BlockRun(val block: Block, startMs: Double) {
    /** Every beat, lead-in first, one interval apart after the start. */
    val allBeats: List<Double> = List(block.leadIn + block.beats) { startMs + (it + 1) * block.intervalMs }
    val beats: List<Double> = allBeats.drop(block.leadIn)
    /** Half a beat after the last one, or a whole beat for holds (the release lands on the last beat). */
    val endMs: Double = allBeats.last() + block.intervalMs * (if (block.hold) 1.0 else 0.5)
    private val downs = ArrayList<Double>()
    private val ups = ArrayList<Double>()
    private val windowStart = beats.first() - block.intervalMs / 2

    /** A key went down (repeats excluded by the caller). Keys the block does not ask for are ignored. */
    fun down(key: RemoteKey, atMs: Double) {
        if (key in block.keys) downs.add(atMs)
    }

    fun up(key: RemoteKey, atMs: Double) {
        if (key in block.keys) ups.add(atMs)
    }

    val presses: List<Double> get() = downs.filter { it >= windowStart && it <= endMs }
    val releases: List<Double> get() = ups.filter { it >= windowStart && it <= endMs }

    fun tempoRun() = TempoRun(block.intervalMs, beats, presses)
}
