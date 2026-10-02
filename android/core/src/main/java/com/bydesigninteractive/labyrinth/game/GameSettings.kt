// Game settings: defaults, the menu's rows, and validation, like maze_game/config.py.
// Storage lives in GameStore (plan 3). Every value travels as a Double: toggles are 0 or
// 1, the size choice is an index into SIZES, zoom is a number of ZOOM_STEP steps.
package com.bydesigninteractive.labyrinth.game

import java.math.BigDecimal
import kotlin.math.floor
import kotlin.math.pow
import kotlin.math.roundToInt

data class GameSettings(
    val followBends: Boolean = true,
    val runStraight: Boolean = false,
    val pauseAtForks: Boolean = true,
    val animated: Boolean = true,
    val multicolor: Boolean = true,
    val showGrid: Boolean = true,
    val glideSpeed: Double = 5.0,
    val turnPause: Double = 0.2,
    val solveSpeed: Double = 20.0,
    val lookahead: Int = 4,
    val genSpeed: Double = 60.0,
    val maxLeads: Int = 12,
    val hintLength: Int = 8,
    val size: String = "medium",
    val customMin: Int = 20,
    val customMax: Int = 40,
    val zoomSteps: Int = 0,
    val coverage: Int = 100,
    val gridStrength: Int = 20,
)

enum class Kind { TOGGLE, NUMBER, CHOICE }

private fun bit(on: Boolean) = if (on) 1.0 else 0.0

/** Steering's choices, by value: Hold to move (0), Run straight (1), Bend assist (2). */
val STEERING_LABELS = listOf("Hold to move", "Run straight", "Bend assist")

private fun steering(s: GameSettings) = if (s.followBends) 2.0 else if (s.runStraight) 1.0 else 0.0

enum class GameField(
    val label: String,
    val kind: Kind,
    val low: Double,
    val high: Double,
    val increment: Double,
    val isInt: Boolean,
    val get: (GameSettings) -> Double,
    val set: (GameSettings, Double) -> GameSettings,
) {
    FOLLOW_BENDS("Bend assist", Kind.TOGGLE, 0.0, 1.0, 1.0, true,
        { bit(it.followBends) }, { s, v -> s.copy(followBends = v != 0.0) }),
    RUN_STRAIGHT("Run straight", Kind.TOGGLE, 0.0, 1.0, 1.0, true,
        { bit(it.runStraight) }, { s, v -> s.copy(runStraight = v != 0.0) }),
    // The menus show Steering in place of the two switches above, which stay stored. It comes
    // after them so a stored Steering wins; an old install without it keeps its Bend assist.
    STEERING("Steering", Kind.CHOICE, 0.0, 2.0, 1.0, true,
        ::steering, { s, v -> s.copy(followBends = v == 2.0, runStraight = v == 1.0) }),
    PAUSE_AT_FORKS("Pause at forks", Kind.TOGGLE, 0.0, 1.0, 1.0, true,
        { bit(it.pauseAtForks) }, { s, v -> s.copy(pauseAtForks = v != 0.0) }),
    LOOKAHEAD("Look-ahead (cells)", Kind.NUMBER, 0.0, 12.0, 1.0, true,
        { it.lookahead.toDouble() }, { s, v -> s.copy(lookahead = v.toInt()) }),
    HINT_LENGTH("Hint length (cells)", Kind.NUMBER, 2.0, 40.0, 1.0, true,
        { it.hintLength.toDouble() }, { s, v -> s.copy(hintLength = v.toInt()) }),
    SOLVE_SPEED("Auto-solve speed (cells/s)", Kind.NUMBER, 2.0, 500.0, 2.0, false,
        { it.solveSpeed }, { s, v -> s.copy(solveSpeed = v) }),
    GLIDE_SPEED("Glide speed (cells/s)", Kind.NUMBER, 2.0, 40.0, 1.0, false,
        { it.glideSpeed }, { s, v -> s.copy(glideSpeed = v) }),
    TURN_PAUSE("Turn pause (s)", Kind.NUMBER, 0.0, 1.0, 0.05, false,
        { it.turnPause }, { s, v -> s.copy(turnPause = v) }),
    SIZE("Size", Kind.CHOICE, 0.0, (SIZES.size - 1).toDouble(), 1.0, true,
        { SIZES.indexOf(it.size).toDouble() }, { s, v -> s.copy(size = SIZES[v.toInt()]) }),
    CUSTOM_MIN("Custom min", Kind.NUMBER, MIN_CUSTOM.toDouble(), MAX_CUSTOM.toDouble(), 1.0, true,
        { it.customMin.toDouble() }, { s, v -> s.copy(customMin = v.toInt()) }),
    CUSTOM_MAX("Custom max", Kind.NUMBER, MIN_CUSTOM.toDouble(), MAX_CUSTOM.toDouble(), 1.0, true,
        { it.customMax.toDouble() }, { s, v -> s.copy(customMax = v.toInt()) }),
    ANIMATED("Animated growth", Kind.TOGGLE, 0.0, 1.0, 1.0, true,
        { bit(it.animated) }, { s, v -> s.copy(animated = v != 0.0) }),
    GEN_SPEED("Growth speed (steps/s per lead)", Kind.NUMBER, 5.0, 1000.0, 5.0, false,
        { it.genSpeed }, { s, v -> s.copy(genSpeed = v) }),
    MAX_LEADS("Max leads", Kind.NUMBER, 2.0, 16.0, 1.0, true,
        { it.maxLeads.toDouble() }, { s, v -> s.copy(maxLeads = v.toInt()) }),
    MULTICOLOR("Colors", Kind.TOGGLE, 0.0, 1.0, 1.0, true,
        { bit(it.multicolor) }, { s, v -> s.copy(multicolor = v != 0.0) }),
    SHOW_GRID("Grid", Kind.TOGGLE, 0.0, 1.0, 1.0, true,
        { bit(it.showGrid) }, { s, v -> s.copy(showGrid = v != 0.0) }),
    GRID_STRENGTH("Grid strength (%)", Kind.NUMBER, 10.0, 100.0, 10.0, true,
        { it.gridStrength.toDouble() }, { s, v -> s.copy(gridStrength = v.toInt()) }),
    COVERAGE("Screen coverage (%)", Kind.NUMBER, 50.0, 100.0, 5.0, true,
        { it.coverage.toDouble() }, { s, v -> s.copy(coverage = v.toInt()) }),
    ZOOM("Zoom", Kind.NUMBER, 0.0, 12.0, 1.0, true,
        { it.zoomSteps.toDouble() }, { s, v -> s.copy(zoomSteps = v.toInt()) });

    /** Accepts a value only if it is in range (and whole, for integer fields). */
    fun validate(value: Double?): Double? {
        if (value == null || value.isNaN()) return null
        if (isInt && value != floor(value)) return null
        return if (value in low..high) value else null
    }

    fun format(value: Double): String = when {
        kind == Kind.TOGGLE -> if (value != 0.0) "On" else "Off"
        this == SIZE -> SIZE_LABELS.getValue(SIZES[value.toInt()])
        this == STEERING -> STEERING_LABELS[value.toInt()]
        this == ZOOM -> "${(100 * ZOOM_STEP.pow(value)).roundToInt()}%"
        value == floor(value) -> value.toLong().toString()
        else -> BigDecimal.valueOf(value).stripTrailingZeros().toPlainString()
    }

    /** A choice's labels, in value order; empty for other kinds. */
    fun choices(): List<String> =
        if (kind != Kind.CHOICE) emptyList() else (low.toInt()..high.toInt()).map { format(it.toDouble()) }
}

/**
 * Build GameSettings from untrusted values. Bad or missing keys keep their defaults. Fields
 * are applied in enum order, so a stored Steering wins over the switches it replaces.
 */
fun gameSettingsFrom(raw: Map<GameField, Double?>): GameSettings {
    var s = GameSettings()
    for (field in GameField.entries) if (field in raw) field.validate(raw[field])?.let { s = field.set(s, it) }
    return s
}

/**
 * Steps a number or choice by its increment, faster the longer the button is held (the
 * same speeds as the settings screen), snapped to the increment and clamped to range.
 */
fun adjust(settings: GameSettings, field: GameField, sign: Int, repeatCount: Int): GameSettings {
    if (field.kind == Kind.TOGGLE) return settings
    val multiplier = when {
        repeatCount >= 20 -> 10
        repeatCount >= 8 -> 5
        else -> 1
    }
    val raw = (field.get(settings) + sign * field.increment * multiplier).coerceIn(field.low, field.high)
    val snapped = Math.round(Math.round(raw / field.increment) * field.increment * 1000) / 1000.0
    var next = field.set(settings, snapped.coerceIn(field.low, field.high))
    if (field == GameField.CUSTOM_MIN && next.customMin > next.customMax) next = next.copy(customMax = next.customMin)
    if (field == GameField.CUSTOM_MAX && next.customMax < next.customMin) next = next.copy(customMin = next.customMax)
    return next
}

/** Flips a toggle; any other field is returned unchanged. */
fun toggle(settings: GameSettings, field: GameField): GameSettings =
    if (field.kind == Kind.TOGGLE) field.set(settings, if (field.get(settings) != 0.0) 0.0 else 1.0) else settings
