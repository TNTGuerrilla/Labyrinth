// What the remote test measured (plan 4 fills it in; until then everything is 0 and the
// game plays exactly like the desktop). Milliseconds, as shown on the result screen.
package com.bydesigninteractive.labyrinth.game

data class RemoteProfile(
    val arrowLagMs: Int = 0,
    val okLagMs: Int = 0,
    val soundDelayMs: Int = 0,
    val arrowRepeatCooldownMs: Int = 0,
    val arrowAlternateCooldownMs: Int = 0,
    val okCooldownMs: Int = 0,
    /** Longest gap between the stutters of a held arrow; null when holds are steady. */
    val arrowHoldGapMs: Int? = null,
    val okHoldGapMs: Int? = null,
    val testedAtMillis: Long = 0,
) {
    val lagSeconds: Double get() = arrowLagMs / 1000.0

    val cooldownSeconds: Double get() = maxOf(arrowRepeatCooldownMs, arrowAlternateCooldownMs) / 1000.0

    /** How long a released arrow counts as still held, when holds stutter. */
    val holdGraceSeconds: Double? get() = arrowHoldGapMs?.let { minOf(it + 50, 500) / 1000.0 }
}
