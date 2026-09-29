// One game in play: a Round, the remote's steering, auto-solve, and what the remote test
// measured. Pure logic, like the desktop game's per-frame code in maze_game/app.py; the
// game screen (plan 3) only forwards keys and calls frame().
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell

class GameController(var settings: GameSettings, var remote: RemoteProfile) {
    lateinit var round: Round
        private set
    val keys = KeyboardSteer()
    var auto: AutoSteer? = null
        private set
    private var now = 0.0
    /** Arrow -> when its release takes effect, while holds stutter. */
    private val pendingRelease = HashMap<Int, Double>()

    fun start(r: Round) {
        round = r
        auto = null
        keys.resetRound()
        pendingRelease.clear()
    }

    fun replay() {
        if (round.phase == RoundPhase.GROW) return
        round.replay()
        auto = null
        keys.resetRound()
    }

    /** Turn pause plus the remote's lag and cooldown, in seconds. */
    val forkPause: Double get() = settings.turnPause + remote.lagSeconds + remote.cooldownSeconds

    val dotMoving: Boolean get() = round.phase == RoundPhase.PLAY && round.mover.moving

    val autoSolving: Boolean get() = auto != null

    fun pressArrow(d: Int) {
        // A stuttering remote reports a hold as press, release, press...: a press inside
        // the grace after a release continues the same hold.
        if (pendingRelease.remove(d) != null) return
        val r = round
        if (r.phase == RoundPhase.GROW) {
            r.skipGrowth()
            return
        }
        keys.press(d)
        auto = null
        if (r.phase != RoundPhase.PLAY) return
        if (!r.mover.returning && isReverse(r.mover.frm, r.mover.to, d)) {
            r.reverse()
            keys.request = null
            return
        }
        r.lateTurn(d, remote.lagSeconds)
    }

    fun releaseArrow(d: Int) {
        val grace = remote.holdGraceSeconds
        if (grace == null) keys.release(d) else pendingRelease[d] = now + grace
    }

    /** Forget every held arrow, including releases still waiting out a stutter's grace. */
    fun clearKeys() {
        keys.clear()
        pendingRelease.clear()
    }

    fun skipGrowth() = round.skipGrowth()

    fun hint() = round.hint(settings.hintLength)

    fun flash() = round.flash()

    fun toggleAuto() {
        if (auto != null) {
            auto = null
            return
        }
        val r = round
        if (r.phase != RoundPhase.PLAY) return
        keys.forgetPosition()
        auto = AutoSteer(r.towardEnd, r.end)
        r.assisted = true
    }

    /** Advance one frame. Returns the cells whose drawing changed. */
    fun frame(dt: Double): Set<Cell> {
        now += dt
        if (pendingRelease.isNotEmpty()) {
            val due = pendingRelease.filterValues { it <= now }.keys
            for (d in due) {
                pendingRelease.remove(d)
                keys.release(d)
            }
        }
        keys.tick(dt)
        val r = round
        val before = r.phase
        val changed = HashSet(r.update(dt))
        // A turn buffered while the player could not yet see the maze must not fire.
        if (before == RoundPhase.GROW && r.phase == RoundPhase.PLAY) keys.resetRound()
        if (r.phase == RoundPhase.PLAY) {
            val a = auto
            val s = settings
            changed += if (a != null) {
                r.move(dt * s.solveSpeed, a::choose, assisted = true)
            } else {
                val stops = listOf(r.start, r.end)
                r.move(dt * s.glideSpeed, { cell, came ->
                    keys.choose(r.grid, cell, came, s.followBends, stops, r.end, s.lookahead, forkPause, s.pauseAtForks)
                })
            }
            if (r.phase != RoundPhase.PLAY || auto?.done == true) auto = null
        }
        r.tickTimer(dt)
        return changed
    }
}
