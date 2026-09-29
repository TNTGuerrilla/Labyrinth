// Settings: defaults and validation, ported from maze_saver/config.py. Storage lives in
// SettingsStore; the desktop frame rate cap has no equivalent here (Android paces to vsync).
package com.bydesigninteractive.labyrinth.maze

data class Settings(
    val minCells: Int = 12,
    val maxCells: Int = 40,
    val genSpeed: Double = 60.0,
    val solveSpeed: Double = 20.0,
    val lookahead: Int = 4,
    val holdSeconds: Double = 4.0,
    val maxLeads: Int = 12,
    val coverage: Int = 100, // percent of each screen side a maze may cover
)

/** One adjustable setting: its range (inclusive), step size and how to read and write it. */
enum class Field(
    val label: String,
    val low: Double,
    val high: Double,
    val increment: Double,
    val isInt: Boolean,
    val get: (Settings) -> Double,
    val set: (Settings, Double) -> Settings,
) {
    MIN_CELLS("Minimum rows/columns", 4.0, 200.0, 1.0, true,
        { it.minCells.toDouble() }, { s, v -> s.copy(minCells = v.toInt()) }),
    MAX_CELLS("Maximum rows/columns", 4.0, 200.0, 1.0, true,
        { it.maxCells.toDouble() }, { s, v -> s.copy(maxCells = v.toInt()) }),
    MAX_LEADS("Maximum leads", 2.0, 16.0, 1.0, true,
        { it.maxLeads.toDouble() }, { s, v -> s.copy(maxLeads = v.toInt()) }),
    COVERAGE("Screen coverage (%)", 50.0, 100.0, 5.0, true,
        { it.coverage.toDouble() }, { s, v -> s.copy(coverage = v.toInt()) }),
    GEN_SPEED("Growth speed per lead (steps per second)", 5.0, 1000.0, 5.0, false,
        { it.genSpeed }, { s, v -> s.copy(genSpeed = v) }),
    SOLVE_SPEED("Solve speed (steps per second)", 2.0, 500.0, 1.0, false,
        { it.solveSpeed }, { s, v -> s.copy(solveSpeed = v) }),
    LOOKAHEAD("Look-ahead distance (cells)", 0.0, 12.0, 1.0, true,
        { it.lookahead.toDouble() }, { s, v -> s.copy(lookahead = v.toInt()) }),
    HOLD_SECONDS("Show solved maze for (seconds)", 0.0, 30.0, 0.5, false,
        { it.holdSeconds }, { s, v -> s.copy(holdSeconds = v) });

    /** Accepts a value only if it is in range (and whole, for integer fields). */
    fun validate(value: Double?): Double? {
        if (value == null || value.isNaN()) return null
        if (isInt && value != Math.floor(value)) return null
        return if (value in low..high) value else null
    }

    fun format(value: Double): String =
        if (value == Math.floor(value)) value.toLong().toString() else value.toString()
}

/** Build Settings from untrusted values. Bad or missing keys keep their defaults. */
fun settingsFrom(raw: Map<Field, Double?>): Settings {
    var settings = Settings()
    for ((field, value) in raw) {
        field.validate(value)?.let { settings = field.set(settings, it) }
    }
    if (settings.minCells > settings.maxCells) {
        settings = settings.copy(minCells = settings.maxCells, maxCells = settings.minCells)
    }
    return settings
}
