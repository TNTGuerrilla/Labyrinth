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

    /**
     * The last steering came from touch: bend assist is always on, and the pause at forks
     * leaves out the remote's lag and cooldown, which touch does not have.
     */
    var touch = false
        private set

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

    /** Turn pause plus, for keys, the remote's lag and cooldown, in seconds. */
    val forkPause: Double
        get() = if (touch) settings.turnPause else settings.turnPause + remote.lagSeconds + remote.cooldownSeconds

    val dotMoving: Boolean get() = round.phase == RoundPhase.PLAY && round.mover.moving

    val autoSolving: Boolean get() = auto != null

    fun pressArrow(d: Int) {
        touch = false
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
        // Only a held arrow can stutter. One pressed during growth never became held, and a
        // grace for its release would swallow the first real press of it once play starts.
        if (grace == null || d !in keys.held) keys.release(d) else pendingRelease[d] = now + grace
    }

    /**
     * A swipe: the dot runs that way along corridors and through bends and stops at the next
     * fork, dead end, start or finish. A swipe while it runs is the turn to take at the first
     * cell where that way is open; one that cannot be taken at the next fork is dropped there.
     */
    fun swipe(d: Int) {
        touch = true
        val r = round
        if (r.phase == RoundPhase.GROW) {
            r.skipGrowth()
            return
        }
        keys.press(d)
        keys.release(d) // a request with nothing held
        auto = null
        if (r.phase != RoundPhase.PLAY) return
        if (!r.mover.returning && isReverse(r.mover.frm, r.mover.to, d)) {
            r.reverse()
            keys.request = null
        }
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
                keys.coast = touch
                r.move(dt * s.glideSpeed, { cell, came ->
                    keys.choose(r.grid, cell, came, s.followBends || touch, stops, r.end, s.lookahead, forkPause, s.pauseAtForks)
                })
            }
            if (r.phase != RoundPhase.PLAY || auto?.done == true) auto = null
        }
        r.tickTimer(dt)
        return changed
    }
}
