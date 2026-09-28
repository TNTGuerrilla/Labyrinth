// One screen's maze: sizing, endpoint placement, and the phase state machine. Ported from
// maze_saver/board.py. Pure logic: Board.update() reports which cells changed so the
// renderer only redraws those.
package com.bydesigninteractive.labyrinth.maze

import kotlin.random.Random

const val FILL_NUM = 4
const val FILL_DEN = 5 // boards fill 80% of the screen
const val MIN_CELL_PX = 4
const val MAX_STEPS_PER_FRAME = 500
const val MAX_ENDPOINT_TRIES = 1000

const val BLACK_SECONDS = 1.0
const val FIRST_DELAY_MAX = 2.0
const val DOTS_SECONDS = 0.8
const val WELD_FLASH_SECONDS = 0.3

/** 80% of a pixel length, rounded down. */
fun fill(px: Int): Int = px * FILL_NUM / FILL_DEN

data class Geometry(val cols: Int, val rows: Int, val cell: Int, val x: Int, val y: Int) {
    val width: Int get() = cols * cell
    val height: Int get() = rows * cell

    fun cellLeft(c: Cell): Int = x + c.x * cell
    fun cellTop(c: Cell): Int = y + c.y * cell
}

/** Square cells; short side fills 80%; long side random from square up to 80%. */
fun computeGeometry(width: Int, height: Int, minCells: Int, maxCells: Int, rng: Random): Geometry {
    val shortFill = fill(minOf(width, height))
    val longFill = fill(maxOf(width, height))
    var nShort = rng.nextInt(minCells, maxCells + 1)
    nShort = maxOf(2, minOf(nShort, shortFill / MIN_CELL_PX))
    val cell = maxOf(1, shortFill / nShort)
    val nLong = rng.nextInt(nShort, maxOf(nShort, longFill / cell) + 1)
    val (cols, rows) = if (width >= height) nLong to nShort else nShort to nLong
    return Geometry(cols, rows, cell, (width - cols * cell) / 2, (height - rows * cell) / 2)
}

/** Two random cells at least half the board's span apart (Manhattan). */
fun chooseEndpoints(cols: Int, rows: Int, rng: Random): Pair<Cell, Cell> {
    val need = (cols + rows) / 2
    repeat(MAX_ENDPOINT_TRIES) {
        val a = Cell(rng.nextInt(cols), rng.nextInt(rows))
        val b = Cell(rng.nextInt(cols), rng.nextInt(rows))
        if (Math.abs(a.x - b.x) + Math.abs(a.y - b.y) >= need) return a to b
    }
    return Cell(0, 0) to Cell(cols - 1, rows - 1)
}

/** Turns a steps-per-second rate into whole steps per frame. */
class StepAccumulator(var rate: Double) {
    private var acc = 0.0

    fun take(dt: Double): Int {
        acc += dt * rate
        val steps = acc.toInt()
        acc -= steps
        return minOf(steps, MAX_STEPS_PER_FRAME)
    }

    /** How far along the next step is, from 0 up to (not including) 1. */
    val fraction: Double get() = acc
}

enum class Phase { BLACK, DOTS, GENERATE, SOLVE, HOLD }

/** What to redraw this frame: the whole board area and/or specific cells. */
class Changes {
    var clear = false
    val cells = HashSet<Cell>()
}

/** One screen's maze cycle: black, dots, generate, solve, hold, repeat. */
class Board(
    val width: Int,
    val height: Int,
    var settings: Settings,
    private val rng: Random,
    initialDelay: Double = 0.0,
    private val forcedLeads: Int? = null,
) {
    var time = 0.0
        private set
    var phase = Phase.BLACK
        private set

    var geometry: Geometry? = null
        private set
    var grid: Grid? = null
        private set
    var start: Cell? = null
        private set
    var end: Cell? = null
        private set
    val regionOf = HashMap<Cell, Int>()
    var hues = DoubleArray(0)
        private set
    val heads = HashMap<Int, Cell>()
    val welds = HashMap<Edge, Double>()
    /** Edge -> true while it is on the current route (bright), false once backed out of (dim). */
    val trail = HashMap<Edge, Boolean>()
    var dot: Cell? = null
        private set
    /** While the dot glides into [dot]: the cell it left. */
    var glideFrom: Cell? = null
        private set
    /** The trail state the gliding edge had before this move, or null if it had none. */
    var glideOld: Boolean? = null
        private set
    var solved = false
        private set
    /** Hold phases entered: the dream closes What's new on one. */
    var mazesSolved = 0
        private set
    /** Times the board went black for its next maze: the dream restores the full screen on one. */
    var mazesCleared = 0
        private set

    private var genEvents: Iterator<GenEvent>? = null
    private var solveEvents: Iterator<SolveEvent>? = null
    private var steps: StepAccumulator? = null
    private var activeLeads = 0
    private var timer = 0.0
    private var pendingClear = false

    init {
        reset()
        enterBlack(initialDelay)
    }

    private fun reset() {
        geometry = null
        grid = null
        start = null
        end = null
        regionOf.clear()
        hues = DoubleArray(0)
        heads.clear()
        welds.clear()
        trail.clear()
        dot = null
        glideFrom = null
        glideOld = null
        solved = false
        genEvents = null
        solveEvents = null
        steps = null
        activeLeads = 0
    }

    val headCells: Set<Cell> get() = heads.values.toHashSet()

    /**
     * How far the dot has glided from [glideFrom] to [dot]: 0 to 1, and 1 when at rest.
     * One solver step lasts exactly one glide, so the dot moves at a steady speed.
     */
    val glideProgress: Double get() = if (glideFrom == null) 1.0 else steps?.fraction ?: 1.0

    fun update(dt: Double): Changes {
        time += dt
        val changes = Changes()
        expireWelds(changes)
        when (phase) {
            Phase.GENERATE -> runGenerator(dt, changes)
            Phase.SOLVE -> runSolver(dt, changes)
            else -> {
                timer -= dt
                if (timer <= 0) {
                    when (phase) {
                        Phase.BLACK -> enterDots(changes)
                        Phase.DOTS -> enterGenerate()
                        else -> {
                            reset()
                            mazesCleared++
                            enterBlack(0.0)
                        }
                    }
                }
            }
        }
        if (pendingClear) {
            pendingClear = false
            changes.clear = true
            changes.cells.clear()
        }
        return changes
    }

    private fun enterBlack(extraDelay: Double) {
        phase = Phase.BLACK
        timer = BLACK_SECONDS + extraDelay
        pendingClear = true
    }

    private fun enterDots(changes: Changes) {
        val s = settings
        val geo = computeGeometry(width, height, s.minCells, s.maxCells, rng)
        geometry = geo
        val g = Grid(geo.cols, geo.rows)
        grid = g
        val (a, b) = chooseEndpoints(geo.cols, geo.rows, rng)
        start = a
        end = b
        val (count, events) = chooseGenerator(g, rng, s.maxLeads, forcedLeads)
        genEvents = events
        activeLeads = count
        val base = rng.nextDouble()
        hues = DoubleArray(count) { (base + it.toDouble() / count) % 1.0 }
        phase = Phase.DOTS
        timer = DOTS_SECONDS
        changes.cells.add(a)
        changes.cells.add(b)
    }

    private fun enterGenerate() {
        phase = Phase.GENERATE
        steps = StepAccumulator(settings.genSpeed)
    }

    private fun runGenerator(dt: Double, changes: Changes) {
        val acc = steps!!
        acc.rate = settings.genSpeed * maxOf(1, activeLeads)
        val events = genEvents!!
        repeat(acc.take(dt)) {
            if (!events.hasNext()) {
                enterSolve(changes)
                return
            }
            applyGeneration(events.next(), changes)
        }
    }

    private fun applyGeneration(event: GenEvent, changes: Changes) {
        when (event) {
            is Start -> {
                regionOf[event.cell] = event.region
                heads[event.region] = event.cell
                changes.cells.add(event.cell)
            }
            is Carve -> {
                regionOf[event.b] = event.region
                heads[event.region] = event.b
                changes.cells.add(event.a)
                changes.cells.add(event.b)
            }
            is Retreat -> {
                heads[event.region] = event.to
                changes.cells.add(event.from)
                changes.cells.add(event.to)
            }
            is Finish -> {
                heads.remove(event.region)
                activeLeads = maxOf(0, activeLeads - 1)
                changes.cells.add(event.cell)
            }
            is Weld -> {
                welds[edgeKey(event.a, event.b)] = time + WELD_FLASH_SECONDS
                changes.cells.add(event.a)
                changes.cells.add(event.b)
            }
        }
    }

    private fun expireWelds(changes: Changes) {
        val it = welds.entries.iterator()
        while (it.hasNext()) {
            val (edge, until) = it.next()
            if (until <= time) {
                it.remove()
                changes.cells.add(edge.a)
                changes.cells.add(edge.b)
            }
        }
    }

    private fun enterSolve(changes: Changes) {
        phase = Phase.SOLVE
        heads.clear()
        val s = start!!
        dot = s
        solveEvents = solve(grid!!, s, end!!, rng, settings.lookahead)
        steps = StepAccumulator(settings.solveSpeed)
        changes.cells.add(s)
    }

    private fun runSolver(dt: Double, changes: Changes) {
        val events = solveEvents!!
        val count = steps!!.take(dt)
        glideFrom?.let {
            // The gliding dot and its partial trail move every frame, and a step that
            // starts a new glide must also finish drawing the old one.
            changes.cells.add(it)
            changes.cells.add(dot!!)
        }
        repeat(count) {
            val event = if (events.hasNext()) events.next() else null
            if (event == null || event is Solved) {
                solved = true
                mazesSolved++
                phase = Phase.HOLD
                timer = settings.holdSeconds
                glideFrom = null
                return
            }
            val (a, b) = when (event) {
                is Advance -> event.a to event.b
                is Backtrack -> event.a to event.b
                is Solved -> error("unreachable")
            }
            val key = edgeKey(a, b)
            glideOld = trail[key]
            trail[key] = event is Advance
            glideFrom = a
            dot = b
            changes.cells.add(a)
            changes.cells.add(b)
        }
    }
}
