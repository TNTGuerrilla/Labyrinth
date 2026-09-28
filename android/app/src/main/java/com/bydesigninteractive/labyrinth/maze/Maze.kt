// Maze grid and animated maze generators, ported from maze_saver/maze.py.
//
// Generators carve into a Grid and yield one event per animation step. They have no
// Android dependency. Both styles produce a perfect maze (a spanning tree).
package com.bydesigninteractive.labyrinth.maze

import kotlin.random.Random

const val CELLS_PER_EXTRA_LEAD = 250
const val BASE_MAX_LEADS = 4

const val N = 1
const val E = 2
const val S = 4
const val W = 8
val DIRECTIONS = intArrayOf(N, E, S, W)

fun dx(d: Int): Int = when (d) { E -> 1; W -> -1; else -> 0 }
fun dy(d: Int): Int = when (d) { S -> 1; N -> -1; else -> 0 }
fun opposite(d: Int): Int = when (d) { N -> S; E -> W; S -> N; else -> E }

/** Ordered like a Python (x, y) tuple so edge keys match the original. */
data class Cell(val x: Int, val y: Int) : Comparable<Cell> {
    override fun compareTo(other: Cell): Int =
        if (x != other.x) x.compareTo(other.x) else y.compareTo(other.y)

    fun step(d: Int): Cell = Cell(x + dx(d), y + dy(d))
}

data class Edge(val a: Cell, val b: Cell)

fun edgeKey(a: Cell, b: Cell): Edge = if (a <= b) Edge(a, b) else Edge(b, a)

fun direction(a: Cell, b: Cell): Int {
    for (d in DIRECTIONS) {
        if (b.x - a.x == dx(d) && b.y - a.y == dy(d)) return d
    }
    throw IllegalArgumentException("cells $a and $b are not adjacent")
}

/** cols x rows cells; each cell stores a bitmask of its open sides. */
class Grid(val cols: Int, val rows: Int) {
    private val open: IntArray

    init {
        require(cols >= 1 && rows >= 1) { "grid must be at least 1x1, got ${cols}x$rows" }
        open = IntArray(cols * rows)
    }

    fun cells(): Sequence<Cell> = sequence {
        for (y in 0 until rows) for (x in 0 until cols) yield(Cell(x, y))
    }

    fun inBounds(c: Cell): Boolean = c.x in 0 until cols && c.y in 0 until rows

    fun neighbors(c: Cell): List<Cell> = DIRECTIONS.map { c.step(it) }.filter { inBounds(it) }

    fun openDirs(c: Cell): Int = open[c.y * cols + c.x]

    fun isOpen(a: Cell, b: Cell): Boolean = openDirs(a) and direction(a, b) != 0

    fun openNeighbors(c: Cell): List<Cell> {
        val bits = openDirs(c)
        return DIRECTIONS.filter { bits and it != 0 }.map { c.step(it) }
    }

    fun carve(a: Cell, b: Cell) {
        val d = direction(a, b)
        require(inBounds(a) && inBounds(b)) { "cannot carve outside the grid: $a -> $b" }
        open[a.y * cols + a.x] = open[a.y * cols + a.x] or d
        open[b.y * cols + b.x] = open[b.y * cols + b.x] or opposite(d)
    }

    fun passageCount(): Int = open.sumOf { Integer.bitCount(it) } / 2
}

sealed interface GenEvent
data class Start(val cell: Cell, val region: Int) : GenEvent
data class Carve(val a: Cell, val b: Cell, val region: Int) : GenEvent
data class Retreat(val from: Cell, val to: Cell, val region: Int) : GenEvent
data class Finish(val cell: Cell, val region: Int) : GenEvent
data class Weld(val a: Cell, val b: Cell) : GenEvent

/** One recursive-backtracker head. step() performs one animation step. */
private class Snake(
    val grid: Grid, start: Cell, val region: Int, val visited: MutableSet<Cell>, val rng: Random,
) {
    val stack = ArrayList<Cell>().apply { add(start) }

    val done: Boolean get() = stack.isEmpty()

    fun step(): GenEvent {
        val cur = stack.last()
        val options = grid.neighbors(cur).filter { it !in visited }
        if (options.isNotEmpty()) {
            val next = options.random(rng)
            grid.carve(cur, next)
            visited.add(next)
            stack.add(next)
            return Carve(cur, next, region)
        }
        stack.removeAt(stack.lastIndex)
        return if (stack.isNotEmpty()) Retreat(cur, stack.last(), region) else Finish(cur, region)
    }
}

fun singleSnake(grid: Grid, rng: Random): Iterator<GenEvent> = iterator {
    val start = Cell(rng.nextInt(grid.cols), rng.nextInt(grid.rows))
    val snake = Snake(grid, start, 0, hashSetOf(start), rng)
    yield(Start(start, 0))
    while (!snake.done) yield(snake.step())
}

fun multiSnake(grid: Grid, rng: Random, heads: Int): Iterator<GenEvent> = iterator {
    val count = heads.coerceIn(1, grid.cols * grid.rows)
    val starts = grid.cells().toMutableList().apply { shuffle(rng) }.take(count)
    val visited = HashSet(starts)
    val regionOf = HashMap<Cell, Int>()
    starts.forEachIndexed { r, c -> regionOf[c] = r }
    val snakes = starts.mapIndexed { r, c -> Snake(grid, c, r, visited, rng) }
    starts.forEachIndexed { r, c -> yield(Start(c, r)) }
    val active = snakes.toMutableList()
    while (active.isNotEmpty()) {
        for (snake in active.toList()) {
            val event = snake.step()
            if (event is Carve) regionOf[event.b] = event.region
            yield(event)
            if (snake.done) active.remove(snake)
        }
    }
    yieldAll(weldRegions(grid, rng, regionOf, count))
}

/** Open one wall per pair of regions needed to join them (Kruskal over regions). */
private fun weldRegions(grid: Grid, rng: Random, regionOf: Map<Cell, Int>, count: Int): Iterator<Weld> =
    iterator {
        val walls = ArrayList<Edge>()
        for (c in grid.cells()) {
            for (n in listOf(c.step(E), c.step(S))) {
                if (grid.inBounds(n) && regionOf[c] != regionOf[n]) walls.add(Edge(c, n))
            }
        }
        walls.shuffle(rng)
        val parent = IntArray(count) { it }

        fun find(start: Int): Int {
            var r = start
            while (parent[r] != r) {
                parent[r] = parent[parent[r]]
                r = parent[r]
            }
            return r
        }

        for ((a, b) in walls) {
            val ra = find(regionOf.getValue(a))
            val rb = find(regionOf.getValue(b))
            if (ra != rb) {
                parent[ra] = rb
                grid.carve(a, b)
                yield(Weld(a, b))
            }
        }
    }

/**
 * Pick a growth style. Returns (region count, event iterator).
 *
 * Without forcedHeads, style is a 50/50 coin flip; the multi-snake head count scales with
 * board size, from 2 up to maxHeads. With forcedHeads, that style and count are used
 * directly: 1 forces a single snake, 2+ forces multi snake with that many heads, clamped
 * to the cell count.
 */
fun chooseGenerator(
    grid: Grid, rng: Random, maxHeads: Int = 12, forcedHeads: Int? = null,
): Pair<Int, Iterator<GenEvent>> {
    val cells = grid.cols * grid.rows
    if (forcedHeads != null) {
        if (forcedHeads <= 1) return 1 to singleSnake(grid, rng)
        val heads = minOf(forcedHeads, cells)
        return heads to multiSnake(grid, rng, heads)
    }
    if (rng.nextDouble() < 0.5) return 1 to singleSnake(grid, rng)
    val upper = maxOf(2, minOf(maxHeads, BASE_MAX_LEADS + cells / CELLS_PER_EXTRA_LEAD))
    val heads = minOf(rng.nextInt(2, upper + 1), cells)
    return heads to multiSnake(grid, rng, heads)
}
