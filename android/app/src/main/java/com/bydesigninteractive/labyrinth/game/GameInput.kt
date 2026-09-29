// What each remote button does on the game screen, given what is showing. Pure; the
// activity maps Android key codes to RemoteKey and carries out the commands.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W

enum class RemoteKey { UP, DOWN, LEFT, RIGHT, OK, BACK, VOLUME_UP, VOLUME_DOWN, OTHER }

sealed interface Command {
    data class Press(val d: Int) : Command
    data class Release(val d: Int) : Command
    data object SkipGrowth : Command
    data object OpenMenu : Command
    data class Menu(val key: MenuKey, val repeatCount: Int) : Command
    data class Zoom(val steps: Int) : Command
    data object Leave : Command
    data object BackHint : Command
    /** 0 is New maze, 1 is Replay. */
    data class WinPick(val choice: Int) : Command
    data class WinConfirm(val choice: Int) : Command
}

data class InputState(
    val menuOpen: Boolean,
    val phase: RoundPhase,
    /** The win panel is showing (not just the win pulse). */
    val winScreen: Boolean,
    /** The timer has started and the maze is not solved yet. */
    val mazeInProgress: Boolean,
)

const val BACK_AGAIN_SECONDS = 2.0

private fun arrow(key: RemoteKey): Int? = when (key) {
    RemoteKey.UP -> N
    RemoteKey.RIGHT -> E
    RemoteKey.DOWN -> S
    RemoteKey.LEFT -> W
    else -> null
}

class GameInput {
    var winChoice = 0
        private set
    private var backAt: Double? = null

    fun resetWin() {
        winChoice = 0
    }

    /** What a key press does; null means it is not the game's key and Android should handle it. */
    fun down(key: RemoteKey, repeatCount: Int, state: InputState, now: Double): List<Command>? {
        if (state.menuOpen) return menu(key, repeatCount)
        if (key == RemoteKey.BACK) return back(state, now)
        if (state.winScreen) return win(key, repeatCount)
        if (key == RemoteKey.VOLUME_UP || key == RemoteKey.VOLUME_DOWN) {
            return listOf(Command.Zoom(if (key == RemoteKey.VOLUME_UP) 1 else -1))
        }
        if (key == RemoteKey.OK) return if (repeatCount == 0) listOf(Command.OpenMenu) else emptyList()
        if (state.phase == RoundPhase.GROW) return if (repeatCount == 0) listOf(Command.SkipGrowth) else emptyList()
        val d = arrow(key) ?: return null
        return if (repeatCount == 0) listOf(Command.Press(d)) else emptyList()
    }

    /** Releases always reach the steering, so a hold never sticks behind the menu. */
    fun up(key: RemoteKey): List<Command>? = arrow(key)?.let { listOf(Command.Release(it)) }

    private fun menu(key: RemoteKey, repeatCount: Int): List<Command>? {
        val k = when (key) {
            RemoteKey.UP -> MenuKey.UP
            RemoteKey.DOWN -> MenuKey.DOWN
            RemoteKey.LEFT -> MenuKey.LEFT
            RemoteKey.RIGHT -> MenuKey.RIGHT
            RemoteKey.OK -> MenuKey.OK
            RemoteKey.BACK -> MenuKey.BACK
            else -> return null
        }
        return listOf(Command.Menu(k, repeatCount))
    }

    private fun back(state: InputState, now: Double): List<Command> {
        val last = backAt
        if (!state.mazeInProgress || (last != null && now - last <= BACK_AGAIN_SECONDS)) {
            backAt = null
            return listOf(Command.Leave)
        }
        backAt = now
        return listOf(Command.BackHint)
    }

    private fun win(key: RemoteKey, repeatCount: Int): List<Command>? = when (key) {
        RemoteKey.LEFT -> {
            winChoice = 0
            listOf(Command.WinPick(0))
        }
        RemoteKey.RIGHT -> {
            winChoice = 1
            listOf(Command.WinPick(1))
        }
        RemoteKey.OK -> if (repeatCount == 0) listOf(Command.WinConfirm(winChoice)) else emptyList()
        RemoteKey.VOLUME_UP, RemoteKey.VOLUME_DOWN, RemoteKey.OTHER -> null
        else -> emptyList()
    }
}
