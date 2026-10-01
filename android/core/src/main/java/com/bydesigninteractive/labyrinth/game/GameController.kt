// One game in play: a Round, the remote's steering, auto-solve, and what the remote test
// measured. Pure logic, like the desktop game's per-frame code in maze_game/app.py; the
// game screen (plan 3) only forwards keys and calls frame().
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.touch.Trace
import com.bydesigninteractive.labyrinth.touch.tapRoute
import com.bydesigninteractive.labyrinth.touch.uniquePath

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
     * The last steering came from touch: the pause at forks leaves out the remote's lag and
     * cooldown, which touch does not have. Only the joystick, a tap and a drag are touch steering
     * without coasting; a swipe follows the bend assist setting.
     */
    var touch = false
        private set

    /** The last steering was a swipe: coast through corridors (and bends, when bend assist is on). */
    private var swiping = false
    /** The cells a tap or a drag still has the dot walk; while not empty, nothing else steers. */
    private val route = ArrayDeque<Cell>()

    val routing: Boolean get() = route.isNotEmpty()

    /** The cells a drag traced that the dot has not reached; while not empty, the dot walks them. */
    private val trace = Trace()

    val traced: List<Cell> get() = trace.cells

    fun start(r: Round) {
        round = r
        auto = null
        keys.resetRound()
        route.clear()
        trace.clear()
        pendingRelease.clear()
    }

    fun replay() {
        if (round.phase == RoundPhase.GROW) return
        round.replay()
        auto = null
        keys.resetRound()
        route.clear()
        trace.clear()
    }

    /** Turn pause plus, for keys, the remote's lag and cooldown, in seconds. */
    val forkPause: Double
        get() = if (touch) settings.turnPause else settings.turnPause + remote.lagSeconds + remote.cooldownSeconds

    val dotMoving: Boolean get() = round.phase == RoundPhase.PLAY && round.mover.moving

    val autoSolving: Boolean get() = auto != null

    fun pressArrow(d: Int) {
        touch = false
        swiping = false
        route.clear()
        trace.clear()
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
     * A swipe: the dot runs that way along corridors and stops at the next fork, dead end, start
     * or finish. It runs through bends when bend assist is on; with it off it runs straight and
     * stops at bends too. A swipe while it runs is the turn to take at the first
     * cell where that way is open; one that cannot be taken at the next fork is dropped there.
     */
    fun swipe(d: Int) {
        touch = true
        swiping = true
        route.clear()
        trace.clear()
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

    /** The touch joystick pressed [d]: held like a remote arrow, without the remote's lag. */
    fun holdTouch(d: Int) {
        touch = true
        swiping = false
        route.clear()
        trace.clear()
        pendingRelease.remove(d)
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
        }
    }

    fun releaseTouch(d: Int) = keys.release(d)

    /** A tap: walks to [target] when its whole route is allowed (see touch/Route.kt), else false. */
    fun goTo(target: Cell): Boolean {
        val r = round
        if (r.phase != RoundPhase.PLAY) return false
        val path = tapRoute(r.grid, r.visitedCells, startOf(target), target) ?: return false
        follow(path)
        return true
    }

    /**
     * A drag began over [cell] (null: outside the maze). On the trace's last cell it extends the
     * trace; anywhere else the rest of the trace is dropped and tracing starts again from the dot.
     */
    fun traceStart(cell: Cell?) {
        if (cell == null || cell != trace.cells.lastOrNull()) trace.clear()
        if (cell != null) traceEnter(cell)
    }

    /** The dragging finger entered [cell]. */
    fun traceEnter(cell: Cell) {
        val r = round
        if (r.phase != RoundPhase.PLAY) return
        touch = true
        swiping = false
        auto = null
        route.clear()
        keys.clear()
        pendingRelease.clear()
        trace.enter(r.grid, cell, r.mover.to ?: r.mover.frm)
    }

    private fun traceChoose(cell: Cell): Cell? {
        trace.reached(cell)
        val next = trace.cells.firstOrNull() ?: return null
        if (next !in round.grid.openNeighbors(cell)) {
            trace.clear()
            return null
        }
        return next
    }

    /**
     * The cell a route to [target] starts from: where the dot is heading, or, when [target] lies
     * behind a moving dot, the cell it came from (the dot turns around; see follow). A returning
     * dot (after a late turn) is already heading for its [frm], so that is where the route starts.
     */
    private fun startOf(target: Cell): Cell {
        val m = round.mover
        val to = m.to ?: return m.frm
        if (m.returning) return m.frm
        val ahead = uniquePath(round.grid, to, target)
        return if (ahead.size >= 2 && ahead[1] == m.frm) m.frm else to
    }

    private fun follow(path: List<Cell>) {
        touch = true
        swiping = false
        auto = null
        keys.clear()
        pendingRelease.clear()
        route.clear()
        trace.clear()
        val m = round.mover
        if (m.to != null && !m.returning && path.first() == m.frm) round.reverse() // the route starts back the way the dot came
        route.addAll(path)
    }

    private fun routeChoose(cell: Cell): Cell? {
        while (route.firstOrNull() == cell) route.removeFirst()
        val next = route.firstOrNull() ?: return null
        if (next !in round.grid.openNeighbors(cell)) {
            route.clear()
            return null
        }
        return next
    }

    /** Forget every held arrow, including releases still waiting out a stutter's grace. */
    fun clearKeys() {
        keys.clear()
        pendingRelease.clear()
        clearRoute()
    }

    /** End any tap or drag route, for when the finger's lift may have been lost. */
    fun clearRoute() = route.clear()

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
        route.clear()
        trace.clear()
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
            } else if (route.isNotEmpty()) {
                r.move(dt * s.glideSpeed, { cell, _ -> routeChoose(cell) })
            } else if (trace.cells.isNotEmpty()) {
                r.move(dt * s.glideSpeed, { cell, _ -> traceChoose(cell) })
            } else {
                val stops = listOf(r.start, r.end)
                keys.coast = swiping
                r.move(dt * s.glideSpeed, { cell, came ->
                    keys.choose(r.grid, cell, came, s.followBends, stops, r.end, s.lookahead, forkPause, s.pauseAtForks)
                })
            }
            if (r.phase != RoundPhase.PLAY || auto?.done == true) auto = null
            if (r.phase != RoundPhase.PLAY) {
                route.clear()
                trace.clear()
            }
        }
        r.tickTimer(dt)
        return changed
    }
}
