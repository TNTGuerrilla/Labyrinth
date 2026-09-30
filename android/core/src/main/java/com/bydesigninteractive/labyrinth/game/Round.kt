// One maze round: growth, play, win. Ported from maze_game/round.py; pure logic.
//
// Round is a CellSource, so BoardRenderer draws it with the screensaver's own cell code.
// The dot itself is drawn separately, as an overlay, so the source reports no glide.
//
// TV addition: lateTurn() lets a turn pressed up to the remote's lag after the dot left a
// fork still count, taking back the overshoot as if it never happened.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Carve
import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.CellSource
import com.bydesigninteractive.labyrinth.maze.Edge
import com.bydesigninteractive.labyrinth.maze.Finish
import com.bydesigninteractive.labyrinth.maze.GenEvent
import com.bydesigninteractive.labyrinth.maze.Grid
import com.bydesigninteractive.labyrinth.maze.Retreat
import com.bydesigninteractive.labyrinth.maze.Start
import com.bydesigninteractive.labyrinth.maze.StepAccumulator
import com.bydesigninteractive.labyrinth.maze.WELD_FLASH_SECONDS
import com.bydesigninteractive.labyrinth.maze.Weld
import com.bydesigninteractive.labyrinth.maze.chooseEndpoints
import com.bydesigninteractive.labyrinth.maze.chooseGenerator
import com.bydesigninteractive.labyrinth.maze.direction
import com.bydesigninteractive.labyrinth.maze.edgeKey
import com.bydesigninteractive.labyrinth.maze.opposite
import kotlin.random.Random

const val SINGLE_HUE = 0.58 // steel blue, used for every region when Colors is off
const val HINT_SECONDS = 2.0
const val FLASH_SECONDS = 1.5
const val WIN_PULSE_SECONDS = 1.0
const val WIN_OVERLAY_DELAY = 1.0
private const val FAST_FORWARD_BUDGET = 0.004 // seconds of growth work per frame while fast-forwarding
private const val FAST_FORWARD_CHUNK = 64 // events applied between clock checks

enum class RoundPhase { GROW, PLAY, WON }

/** The latest logical move, kept so a late turn can take it back. */
private class LastMove(val a: Cell, val b: Cell, val step: TrailStep, val isNew: Boolean, val assisted: Boolean)

class Round private constructor(
    override val grid: Grid,
    override val start: Cell,
    override val end: Cell,
    regionCount: Int,
    private val gen: Iterator<GenEvent>,
    settings: GameSettings,
    rng: Random,
    private val clock: () -> Double,
) : CellSource {
    val regionHues: DoubleArray = run {
        val base = rng.nextDouble()
        DoubleArray(regionCount) { (base + it.toDouble() / regionCount) % 1.0 }
    }
    override var hues: DoubleArray = DoubleArray(0)
        private set
    var multicolor: Boolean = false
        set(value) {
            field = value
            hues = if (value) regionHues.copyOf() else DoubleArray(regionHues.size) { SINGLE_HUE }
        }
    var genSpeed: Double = settings.genSpeed
    override val regionOf = HashMap<Cell, Int>()
    val heads = HashMap<Int, Cell>()
    override val headCells = HashSet<Cell>()
    override val welds = HashMap<Edge, Double>()
    var time = 0.0
        private set
    var shortest = 0
        private set
    var towardEnd: Map<Cell, Cell> = emptyMap()
        private set
    var phase = RoundPhase.GROW
        private set
    var fastForward = !settings.animated
        private set
    private var activeLeads = regionCount
    private val steps = StepAccumulator(settings.genSpeed)
    private val pendingChanged = HashSet<Cell>()

    var mover = Mover(start)
        private set
    var path = Trail(start)
        private set
    var explored = 0
        private set
    var autoExplored = 0
        private set
    private val visited = HashSet<Cell>()
    /** Cells the dot has entered this round, the start included (read-only). */
    val visitedCells: Set<Cell> get() = visited
    var hints = 0
        private set
    var elapsed = 0.0
        private set
    var timerRunning = false
        private set
    var assisted = false
    var wonAt: Double? = null
        private set
    var hintRoute: List<Cell> = emptyList()
        private set
    var hintAt: Double? = null
        private set
    var flashAt: Double? = null
        private set
    private var lastMove: LastMove? = null
    private var departCell: Cell? = null
    private var departTo: Cell? = null
    private var departAt = 0.0

    init {
        multicolor = settings.multicolor
        resetPlay()
    }

    companion object {
        fun create(
            cols: Int, rows: Int, settings: GameSettings, rng: Random,
            clock: () -> Double = { System.nanoTime() / 1e9 },
        ): Round {
            val grid = Grid(cols, rows)
            val (start, end) = chooseEndpoints(cols, rows, rng)
            val (count, gen) = chooseGenerator(grid, rng, settings.maxLeads)
            return Round(grid, start, end, count, gen, settings, rng, clock)
        }

        /** A round over an already carved maze, straight into play. */
        fun ofMaze(grid: Grid, start: Cell, end: Cell, settings: GameSettings): Round {
            val r = Round(grid, start, end, 1, emptyList<GenEvent>().iterator(), settings, Random(0)) { 0.0 }
            for (c in grid.cells()) r.regionOf[c] = 0
            r.finishGrowthNow()
            return r
        }
    }

    // --- drawing (CellSource) ----------------------------------------------------

    override val trail: Map<Edge, Boolean> get() = path.edges
    override val dot: Cell get() = mover.cell
    override val glideFrom: Cell? get() = null
    override val glideOld: Boolean? get() = null
    override val glideProgress: Double get() = 1.0

    // --- growth --------------------------------------------------------------------

    /** Advance the clock, expire weld flashes and run growth. Returns changed cells. */
    fun update(dt: Double): Set<Cell> {
        time += dt
        val changed = HashSet<Cell>(pendingChanged)
        pendingChanged.clear()
        val it = welds.entries.iterator()
        while (it.hasNext()) {
            val (edge, until) = it.next()
            if (until <= time) {
                it.remove()
                changed.add(edge.a)
                changed.add(edge.b)
            }
        }
        if (phase == RoundPhase.GROW) {
            if (fastForward) {
                runFastForward(changed)
            } else {
                steps.rate = genSpeed * maxOf(1, activeLeads)
                repeat(steps.take(dt)) { if (!stepGrowth(changed)) return changed }
            }
        }
        return changed
    }

    /** Ends every weld flash now (the game is pausing). The cells are reported by the next update(). */
    fun endWeldFlashes() {
        for (edge in welds.keys) { pendingChanged.add(edge.a); pendingChanged.add(edge.b) }
        welds.clear()
    }

    fun skipGrowth() {
        if (phase == RoundPhase.GROW) fastForward = true
    }

    fun finishGrowthNow() {
        val scratch = HashSet<Cell>()
        while (phase == RoundPhase.GROW) {
            stepGrowth(scratch)
            scratch.clear()
        }
    }

    private fun runFastForward(changed: MutableSet<Cell>) {
        val deadline = clock() + FAST_FORWARD_BUDGET
        while (phase == RoundPhase.GROW) {
            repeat(FAST_FORWARD_CHUNK) { if (!stepGrowth(changed)) return }
            if (clock() >= deadline) return
        }
    }

    /** Apply one generator event. Returns false once growth has finished. */
    private fun stepGrowth(changed: MutableSet<Cell>): Boolean {
        if (!gen.hasNext()) {
            finishGrowth()
            return false
        }
        apply(gen.next(), changed)
        return true
    }

    private fun finishGrowth() {
        heads.clear()
        headCells.clear()
        towardEnd = buildTowardEnd(grid, end)
        var count = 0
        var c = start
        while (c != end) {
            c = towardEnd.getValue(c)
            count++
        }
        shortest = count
        phase = RoundPhase.PLAY
    }

    private fun setHead(region: Int, cell: Cell) {
        heads[region]?.let { headCells.remove(it) }
        heads[region] = cell
        headCells.add(cell)
    }

    private fun apply(event: GenEvent, changed: MutableSet<Cell>) {
        when (event) {
            is Start -> {
                regionOf[event.cell] = event.region
                setHead(event.region, event.cell)
                changed.add(event.cell)
            }
            is Carve -> {
                regionOf[event.b] = event.region
                setHead(event.region, event.b)
                changed.add(event.a)
                changed.add(event.b)
            }
            is Retreat -> {
                setHead(event.region, event.to)
                changed.add(event.from)
                changed.add(event.to)
            }
            is Finish -> {
                heads.remove(event.region)?.let { headCells.remove(it) }
                activeLeads = maxOf(0, activeLeads - 1)
                changed.add(event.cell)
            }
            is Weld -> {
                welds[edgeKey(event.a, event.b)] = time + WELD_FLASH_SECONDS
                changed.add(event.a)
                changed.add(event.b)
            }
        }
    }

    // --- play ----------------------------------------------------------------------

    private fun resetPlay() {
        mover = Mover(start)
        path = Trail(start)
        explored = 0
        autoExplored = 0
        visited.clear()
        visited.add(start)
        hints = 0
        elapsed = 0.0
        timerRunning = false
        assisted = false
        wonAt = null
        hintRoute = emptyList()
        hintAt = null
        flashAt = null
        lastMove = null
        departCell = null
        departTo = null
    }

    /** Glide up to [distance] cells. Returns cells whose drawing changed. */
    fun move(distance: Double, choose: Chooser, assisted: Boolean = false): Set<Cell> {
        val changed = HashSet<Cell>()
        if (phase != RoundPhase.PLAY) return changed
        val tracked: Chooser = { cell, came ->
            choose(cell, came)?.also {
                departCell = cell
                departTo = it
                departAt = time
            }
        }
        for ((a, b) in mover.advance(distance, tracked)) {
            val step = path.move(a, b)
            val isNew = visited.add(b)
            if (isNew) {
                if (assisted) autoExplored++ else explored++
            }
            lastMove = LastMove(a, b, step, isNew, assisted)
            timerRunning = true
            changed.add(a)
            changed.add(b)
            if (b == end) {
                phase = RoundPhase.WON
                timerRunning = false
                wonAt = time
                mover.place(end)
                break
            }
        }
        return changed
    }

    /**
     * A turn toward [d] pressed after the dot left a cell center where d was open. If it
     * left no more than [window] seconds ago and is still on that segment, the dot returns
     * to the center; a move already recorded on the way out is taken back (not explored,
     * not dimmed). The caller's steering then takes the turn at the center.
     */
    fun lateTurn(d: Int, window: Double): Boolean {
        if (phase != RoundPhase.PLAY || window <= 0) return false
        val from = departCell ?: return false
        val to = mover.to ?: return false
        if (mover.returning || mover.frm != from || to != departTo || time - departAt > window) return false
        val taken = direction(from, to)
        if (d == taken || d == opposite(taken) || (grid.openDirs(from) and d) == 0) return false
        val last = lastMove
        if (mover.t >= 0.5 && last != null && last.a == from && last.b == to) {
            path.undo(from, to, last.step)
            if (last.isNew) {
                visited.remove(to)
                if (last.assisted) autoExplored-- else explored--
            }
            lastMove = null
            pendingChanged.add(from)
            pendingChanged.add(to)
        }
        mover.pullBack()
        departCell = null
        return true
    }

    fun reverse() {
        if (phase == RoundPhase.PLAY) mover.reverse()
    }

    fun tickTimer(dt: Double) {
        if (timerRunning) elapsed += dt
    }

    fun hint(length: Int) {
        if (phase != RoundPhase.PLAY) return
        val route = ArrayList<Cell>()
        var c = mover.cell
        for (i in 0 until length) {
            if (c == end) break
            c = towardEnd.getValue(c)
            route.add(c)
        }
        hintRoute = route
        hints++
        hintAt = time
    }

    fun flash() {
        if (phase != RoundPhase.GROW) flashAt = time
    }

    fun replay() {
        if (phase == RoundPhase.GROW) return
        resetPlay()
        phase = RoundPhase.PLAY
    }

    val efficiency: Int get() {
        val total = explored + autoExplored
        return if (total == 0) 0 else Math.round(100.0 * shortest / total).toInt()
    }

    val hintActive: Boolean get() = hintAt?.let { time - it < HINT_SECONDS } ?: false
    val flashActive: Boolean get() = flashAt?.let { time - it < FLASH_SECONDS } ?: false
    val winPulseActive: Boolean get() = phase == RoundPhase.WON && wonAt?.let { time - it < WIN_PULSE_SECONDS } ?: false
    val winOverlayVisible: Boolean get() = phase == RoundPhase.WON && wonAt?.let { time - it >= WIN_OVERLAY_DELAY } ?: false
}
