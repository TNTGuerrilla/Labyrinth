// The in-game menu opened with OK: its tabs and rows, and what each remote key does in it.
// Pure state; GameActivity (play/) draws it and carries out the effects.
package com.bydesigninteractive.labyrinth.game

enum class Tab(val title: String) {
    CONTROLS("Controls"), PLAY("Play"), MAZE("Maze"), ASSISTS("Assists"), MOVEMENT("Movement"), LOOK("Look"),
}

enum class MenuAction(val label: String) {
    RESUME("Resume"), HINT("Hint"), AUTO_SOLVE("Auto-solve"), FLASH("Flash finish"), REPLAY("Replay"), NEW_MAZE("New maze"), TEST_REMOTE("Test remote"),
}

sealed interface Row {
    data class Text(val text: String) : Row
    data class Action(val action: MenuAction) : Row
    data class Setting(val field: GameField) : Row
}

val Row.selectable: Boolean get() = this !is Row.Text

val CONTROLS_TEXT = listOf(
    "Arrows: steer the dot.",
    "OK: open this menu.",
    "Back: leave the game. During a maze, press it twice.",
    "Volume up and down: zoom in and out, on TVs that pass those buttons to apps.",
    "While the maze grows, any other button skips to the finished maze.",
    "In this menu: left and right switch tabs, up and down pick a row, OK changes it, Back closes the menu.",
    "On a number, OK starts editing: left and right change it, and OK or Back finishes.",
)

val PLAY_ACTIONS = listOf(
    MenuAction.RESUME, MenuAction.HINT, MenuAction.AUTO_SOLVE, MenuAction.FLASH, MenuAction.REPLAY, MenuAction.NEW_MAZE,
)

const val LAG_NOTE = "Your remote's lag is added to the pause at forks, and a turn pressed up to that late " +
    "still counts. Test again if you change remotes or the TV's picture mode."

fun rows(tab: Tab, s: GameSettings): List<Row> = when (tab) {
    Tab.CONTROLS -> CONTROLS_TEXT.map { Row.Text(it) }
    Tab.PLAY -> PLAY_ACTIONS.map { Row.Action(it) }
    Tab.MAZE -> listOfNotNull(
        Row.Setting(GameField.SIZE),
        if (s.size == "custom") Row.Setting(GameField.CUSTOM_MIN) else null,
        if (s.size == "custom") Row.Setting(GameField.CUSTOM_MAX) else null,
        Row.Setting(GameField.ANIMATED),
        Row.Setting(GameField.GEN_SPEED),
        Row.Setting(GameField.MAX_LEADS),
    )
    Tab.ASSISTS -> listOfNotNull(
        Row.Setting(GameField.FOLLOW_BENDS),
        if (!s.followBends) Row.Setting(GameField.PAUSE_AT_FORKS) else null,
        Row.Setting(GameField.LOOKAHEAD),
        Row.Setting(GameField.HINT_LENGTH),
        Row.Setting(GameField.SOLVE_SPEED),
    )
    Tab.MOVEMENT -> listOf(
        Row.Setting(GameField.GLIDE_SPEED),
        Row.Setting(GameField.TURN_PAUSE),
        Row.Action(MenuAction.TEST_REMOTE),
        Row.Text(LAG_NOTE),
    )
    Tab.LOOK -> listOf(Row.Setting(GameField.MULTICOLOR), Row.Setting(GameField.SHOW_GRID), Row.Setting(GameField.ZOOM))
}

const val MENU_RESET_SECONDS = 60.0

enum class MenuKey { LEFT, RIGHT, UP, DOWN, OK, BACK }

sealed interface MenuEffect {
    data object None : MenuEffect
    data object Closed : MenuEffect
    /** The menu has closed; run the action. */
    data class Run(val action: MenuAction) : MenuEffect
    data class Changed(val settings: GameSettings) : MenuEffect
}

/** A size change starts a new maze when the menu closes; other Maze rows wait for the next one. */
fun needsNewMaze(before: GameSettings, after: GameSettings): Boolean =
    before.size != after.size ||
        (after.size == "custom" && (before.customMin != after.customMin || before.customMax != after.customMax))

class MenuModel {
    var isOpen = false
        private set
    var tab = Tab.PLAY
        private set
    var editing = false
        private set
    private val selected = HashMap<Tab, Int>()
    private var closedAt: Double? = null

    /**
     * Opens on [first] if given. Otherwise it opens where it was left, unless it has been
     * closed for more than a minute (or never opened), in which case Play > Resume.
     */
    fun open(now: Double, first: Tab? = null) {
        isOpen = true
        editing = false
        val closed = closedAt
        if (first != null) {
            tab = first
        } else if (closed == null || now - closed > MENU_RESET_SECONDS) {
            tab = Tab.PLAY
            selected[Tab.PLAY] = 0
        }
    }

    /** Coming back to the game from elsewhere (Home): Play > Resume. */
    fun openAtResume() {
        isOpen = true
        editing = false
        tab = Tab.PLAY
        selected[Tab.PLAY] = 0
    }

    fun close(now: Double) {
        isOpen = false
        editing = false
        closedAt = now
    }

    /** Index among the current tab's selectable rows, or -1 when it has none. */
    fun selectedIndex(s: GameSettings): Int {
        val n = rows(tab, s).count { it.selectable }
        if (n == 0) return -1
        return (selected[tab] ?: 0).coerceIn(0, n - 1)
    }

    fun selectedRow(s: GameSettings): Row? = rows(tab, s).filter { it.selectable }.getOrNull(selectedIndex(s))

    fun key(key: MenuKey, s: GameSettings, now: Double, repeatCount: Int = 0): MenuEffect {
        if (!isOpen) return MenuEffect.None
        if (editing) {
            val field = (selectedRow(s) as? Row.Setting)?.field
            return when (key) {
                MenuKey.LEFT, MenuKey.RIGHT ->
                    if (field == null) MenuEffect.None
                    else MenuEffect.Changed(adjust(s, field, if (key == MenuKey.RIGHT) 1 else -1, repeatCount))
                MenuKey.OK, MenuKey.BACK -> {
                    editing = false
                    MenuEffect.None
                }
                else -> MenuEffect.None
            }
        }
        val tabs = Tab.entries
        return when (key) {
            MenuKey.LEFT -> {
                tab = tabs[(tab.ordinal + tabs.size - 1) % tabs.size]
                MenuEffect.None
            }
            MenuKey.RIGHT -> {
                tab = tabs[(tab.ordinal + 1) % tabs.size]
                MenuEffect.None
            }
            MenuKey.UP -> move(-1, s)
            MenuKey.DOWN -> move(1, s)
            MenuKey.BACK -> {
                close(now)
                MenuEffect.Closed
            }
            MenuKey.OK -> when (val row = selectedRow(s)) {
                is Row.Action -> {
                    close(now)
                    MenuEffect.Run(row.action)
                }
                is Row.Setting ->
                    if (row.field.kind == Kind.TOGGLE) {
                        MenuEffect.Changed(toggle(s, row.field))
                    } else {
                        editing = true
                        MenuEffect.None
                    }
                else -> MenuEffect.None
            }
        }
    }

    private fun move(delta: Int, s: GameSettings): MenuEffect {
        val n = rows(tab, s).count { it.selectable }
        if (n > 0) selected[tab] = (selectedIndex(s) + delta).coerceIn(0, n - 1)
        return MenuEffect.None
    }
}
