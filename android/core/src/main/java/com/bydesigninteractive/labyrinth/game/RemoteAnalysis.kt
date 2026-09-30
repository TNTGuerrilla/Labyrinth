// What the remote test's timestamps say about the remote. Pure functions over
// milliseconds on one clock (the beats as scheduled, the presses as Android stamped them).
package com.bydesigninteractive.labyrinth.game

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** One block of beats at one tempo and the presses recorded during it. */
data class TempoRun(val intervalMs: Double, val beats: List<Double>, val presses: List<Double>)

/**
 * How late each matched press was. A press matches the nearest beat within half an
 * interval; each beat takes only its first press; early presses count as 0.
 */
fun offsets(beats: List<Double>, presses: List<Double>, intervalMs: Double): List<Double> {
    val used = HashSet<Int>()
    val out = ArrayList<Double>()
    for (p in presses.sorted()) {
        val i = beats.indices.minByOrNull { abs(beats[it] - p) } ?: continue
        if (abs(beats[i] - p) > intervalMs / 2 || !used.add(i)) continue
        out.add(max(0.0, p - beats[i]))
    }
    return out
}

fun median(values: List<Double>): Double {
    require(values.isNotEmpty()) { "median of nothing" }
    val s = values.sorted()
    val n = s.size
    return if (n % 2 == 1) s[n / 2] else (s[n / 2 - 1] + s[n / 2]) / 2
}

/** Median lateness over all the runs, or null when fewer than [need] presses matched. */
fun lagMs(runs: List<TempoRun>, need: Int): Int? {
    val all = runs.flatMap { offsets(it.beats, it.presses, it.intervalMs) }
    return if (all.size < need) null else median(all).roundToInt()
}

/**
 * A cooldown shows as a floor: at tempos where presses go missing, the presses that did
 * register are never closer together than the cooldown. Random misses leave neighbors one
 * interval apart, so they have no floor. Blocks with fewer than two presses say nothing.
 * Returns the floor rounded to 10 ms, or 0 for none.
 */
fun cooldownMs(runs: List<TempoRun>): Int {
    var dropping = 0
    var floor = Double.MAX_VALUE
    for (r in runs) {
        if (offsets(r.beats, r.presses, r.intervalMs).size >= 0.75 * r.beats.size) continue
        val sorted = r.presses.sorted()
        if (sorted.size < 2) continue
        val minGap = sorted.zipWithNext { a, b -> b - a }.minOrNull() ?: return 0
        if (minGap < 1.3 * r.intervalMs) return 0
        dropping++
        floor = min(floor, minGap)
    }
    return if (dropping >= 2) (floor / 10).roundToInt() * 10 else 0
}

/** Null when the hold came through as one press; otherwise the longest release-to-press gap. */
fun holdGapMs(downs: List<Double>, ups: List<Double>): Int? {
    val d = downs.sorted()
    if (d.size <= 1) return null
    var longest = 0.0
    for (up in ups.sorted()) {
        val next = d.firstOrNull { it > up } ?: continue
        longest = max(longest, next - up)
    }
    return longest.roundToInt()
}
