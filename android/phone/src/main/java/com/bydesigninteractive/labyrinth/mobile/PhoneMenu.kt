// The phone game's menu: its tabs and rows, and the pure rules behind its controls. The
// game's settings (GameField) are shared with the TV; the phone adds how it is steered and
// held, and an About tab. MenuPanel draws it.
package com.bydesigninteractive.labyrinth.mobile

import com.bydesigninteractive.labyrinth.game.GameField
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.MENU_RESET_SECONDS
import com.bydesigninteractive.labyrinth.game.MenuAction
import com.bydesigninteractive.labyrinth.game.PLAY_ACTIONS
import com.bydesigninteractive.labyrinth.touch.Hold
import kotlin.math.roundToInt

enum class PhoneTab(val title: String) {
    CONTROLS("Controls"), PLAY("Play"), MAZE("Maze"), ASSISTS("Assists"), MOVEMENT("Movement"), LOOK("Look"), ABOUT("About"),
}

enum class PhoneChoice(val label: String) { TOUCH("Touch controls"), ORIENTATION("Orientation"), JOYSTICK_HAND("Joystick hand") }

enum class PhoneToggle(val label: String) { HIDE_BARS("Hide system bars"), CHECK_UPDATES("Check for updates") }

enum class MenuLink(val label: String) {
    HOW_TO_PLAY("How to play"), CONTROLLER_TEST("Controller test"),
    UPDATE("Update"), DISMISS("Dismiss"), CHECK_NOW("Check now"), WHATS_NEW("What's new"),
}

sealed interface MenuRow {
    data class Note(val text: String) : MenuRow
    data class Action(val action: MenuAction) : MenuRow
    data class Game(val field: GameField) : MenuRow
    data class Choice(val choice: PhoneChoice) : MenuRow
    data class Toggle(val toggle: PhoneToggle) : MenuRow
    data class Link(val link: MenuLink) : MenuRow
    /** The update line, drawn live by the menu. */
    data object Status : MenuRow
}

const val COPYRIGHT = "\u00a9 2026 ByDesign Interactive"
const val LICENSE_LINE = "Licensed under Apache 2.0"
const val PROJECT_ADDRESS = "github.com/TNTGuerrilla/Labyrinth"
const val SIZE_NOTE = "Sizes are cell widths on your screen: Small 8 mm, Medium 5 mm, Large 3.5 mm, XL 2.5 mm."
const val BENDS_NOTE = "Swipes always follow bends. Bend assist and Pause at forks are for keys and controllers."

val KEY_HELP = listOf(
    "Keyboards and controllers: the arrows, WASD, the D-pad or the left stick steer.",
    "A, Enter or Start opens the menu. B or Esc closes it; during a maze, press Back twice to leave.",
    "Shoulder buttons or + and - zoom. In this menu the shoulder buttons switch tabs.",
)

val HOW_TO_PLAY = listOf(
    "Get the green dot to the red one.",
    "Swipe on the maze to send the dot running. It follows the corridor and stops at the next fork.",
    "Swipe again while it runs to choose the turn at the next fork.",
    "Pinch to zoom. Tap while the maze grows to skip to the finished maze.",
    "Menu has hints, auto-solve, new mazes and settings. Other ways to steer are under Menu > Controls.",
    "Keyboards and controllers work too: the arrows or the D-pad steer, and A or Enter opens the menu.",
)

private val HOLD_LABELS = mapOf(Hold.AUTO to "Auto", Hold.PORTRAIT to "Portrait", Hold.LANDSCAPE to "Landscape")

fun phoneRows(tab: PhoneTab, s: GameSettings, p: PhoneSettings, version: String, controllerUsed: Boolean = false, canUpdate: Boolean = false): List<MenuRow> = when (tab) {
    PhoneTab.CONTROLS -> listOfNotNull(
        MenuRow.Choice(PhoneChoice.TOUCH),
        if (p.touch == TouchScheme.JOYSTICK) MenuRow.Choice(PhoneChoice.JOYSTICK_HAND) else null,
        MenuRow.Note(p.touch.help),
        if (controllerUsed) MenuRow.Link(MenuLink.CONTROLLER_TEST) else null,
    ) + KEY_HELP.map { MenuRow.Note(it) }
    PhoneTab.PLAY -> PLAY_ACTIONS.map { MenuRow.Action(it) }
    PhoneTab.MAZE -> listOfNotNull(
        MenuRow.Game(GameField.SIZE),
        if (s.size == "custom") MenuRow.Game(GameField.CUSTOM_MIN) else null,
        if (s.size == "custom") MenuRow.Game(GameField.CUSTOM_MAX) else null,
        MenuRow.Game(GameField.ANIMATED),
        MenuRow.Game(GameField.GEN_SPEED),
        MenuRow.Game(GameField.MAX_LEADS),
        MenuRow.Note(SIZE_NOTE),
    )
    PhoneTab.ASSISTS -> listOfNotNull(
        MenuRow.Game(GameField.FOLLOW_BENDS),
        if (!s.followBends) MenuRow.Game(GameField.PAUSE_AT_FORKS) else null,
        MenuRow.Game(GameField.LOOKAHEAD),
        MenuRow.Game(GameField.HINT_LENGTH),
        MenuRow.Game(GameField.SOLVE_SPEED),
        MenuRow.Note(BENDS_NOTE),
    )
    PhoneTab.MOVEMENT -> listOf(MenuRow.Game(GameField.GLIDE_SPEED), MenuRow.Game(GameField.TURN_PAUSE))
    PhoneTab.LOOK -> listOfNotNull(
        MenuRow.Game(GameField.MULTICOLOR),
        MenuRow.Game(GameField.SHOW_GRID),
        if (s.showGrid) MenuRow.Game(GameField.GRID_STRENGTH) else null,
        MenuRow.Game(GameField.COVERAGE),
        MenuRow.Game(GameField.ZOOM),
        MenuRow.Choice(PhoneChoice.ORIENTATION),
        MenuRow.Toggle(PhoneToggle.HIDE_BARS),
    )
    PhoneTab.ABOUT -> listOfNotNull(
        MenuRow.Note("Labyrinth Mobile $version"),
        MenuRow.Status,
        if (canUpdate) MenuRow.Link(MenuLink.UPDATE) else null,
        if (canUpdate) MenuRow.Link(MenuLink.DISMISS) else null,
        MenuRow.Link(MenuLink.CHECK_NOW),
        MenuRow.Link(MenuLink.WHATS_NEW),
        MenuRow.Toggle(PhoneToggle.CHECK_UPDATES),
        MenuRow.Link(MenuLink.HOW_TO_PLAY),
        MenuRow.Note(COPYRIGHT),
        MenuRow.Note(LICENSE_LINE),
        MenuRow.Note(PROJECT_ADDRESS),
    )
}

/** The tab a reopened menu shows: the one it closed on within a minute, otherwise Play. */
fun reopenTab(last: PhoneTab, closedAt: Double?, now: Double): PhoneTab =
    if (closedAt != null && now - closedAt <= MENU_RESET_SECONDS) last else PhoneTab.PLAY

fun choiceOptions(c: PhoneChoice): List<String> = when (c) {
    PhoneChoice.TOUCH -> TouchScheme.entries.map { it.label }
    PhoneChoice.ORIENTATION -> Hold.entries.map { HOLD_LABELS.getValue(it) }
    PhoneChoice.JOYSTICK_HAND -> Hand.entries.map { it.label }
}

fun choiceIndex(c: PhoneChoice, p: PhoneSettings): Int = when (c) {
    PhoneChoice.TOUCH -> p.touch.ordinal
    PhoneChoice.ORIENTATION -> p.hold.ordinal
    PhoneChoice.JOYSTICK_HAND -> p.hand.ordinal
}

fun choose(c: PhoneChoice, p: PhoneSettings, i: Int): PhoneSettings = when (c) {
    PhoneChoice.TOUCH -> p.copy(touch = TouchScheme.entries[i])
    PhoneChoice.ORIENTATION -> p.copy(hold = Hold.entries[i])
    PhoneChoice.JOYSTICK_HAND -> p.copy(hand = Hand.entries[i])
}

fun toggleValue(t: PhoneToggle, p: PhoneSettings): Boolean = when (t) {
    PhoneToggle.HIDE_BARS -> p.hideBars
    PhoneToggle.CHECK_UPDATES -> false // held by the updater, not PhoneSettings: MenuPanel asks its host
}

fun flip(t: PhoneToggle, p: PhoneSettings): PhoneSettings = when (t) {
    PhoneToggle.HIDE_BARS -> p.copy(hideBars = !p.hideBars)
    PhoneToggle.CHECK_UPDATES -> p // held by the updater, not PhoneSettings: MenuPanel asks its host
}

/** Slider positions for a number: one per increment from low to high. */
fun sliderSteps(f: GameField): Int = ((f.high - f.low) / f.increment).roundToInt()

fun sliderValue(f: GameField, step: Int): Double =
    Math.round((f.low + step.coerceIn(0, sliderSteps(f)) * f.increment) * 1000) / 1000.0

fun sliderStep(f: GameField, value: Double): Int = ((value - f.low) / f.increment).roundToInt().coerceIn(0, sliderSteps(f))

/** Sets a number, clamped to its range, keeping Custom min at or below Custom max as the buttons do. */
fun setNumber(s: GameSettings, f: GameField, value: Double): GameSettings {
    var next = f.set(s, value.coerceIn(f.low, f.high))
    if (f == GameField.CUSTOM_MIN && next.customMin > next.customMax) next = next.copy(customMax = next.customMin)
    if (f == GameField.CUSTOM_MAX && next.customMax < next.customMin) next = next.copy(customMin = next.customMax)
    return next
}
