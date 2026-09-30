// Maze solvers, ported from maze_saver/solver.py. The default is human-like.
//
// The dot walks a DFS stack like a person tracing a maze with a finger. It can see a
// short distance down each branch (`lookahead` cells from the fork) and will not wander
// into a branch that visibly dead-ends within that distance. At a fork on the true route
// it always takes the correct turn if it can see the finish down that branch; otherwise
// it usually takes the correct turn, but sometimes (MISTAKE_CHANCE) takes a wrong one
// anyway and wanders for a while before giving up and backing out, bounded by a random
// detour budget (DETOUR_MIN..DETOUR_MAX steps).
//
// Three more solvers share its events: depth-first (look-ahead pruning, prefers the
// passage nearest the finish, no detour limit), a left-hand wall follower, and a
// perfect solver that walks the shortest route. solveWith picks one by name.
package com.bydesigninteractive.labyrinth.maze

import kotlin.math.abs
import kotlin.random.Random

const val DEFAULT_LOOKAHEAD = 4
const val MISTAKE_CHANCE = 0.3
const val DETOUR_MIN = 10
const val DETOUR_MAX = 40

sealed interface SolveEvent
data class Advance(val a: Cell, val b: Cell) : SolveEvent
data class Backtrack(val a: Cell, val b: Cell) : SolveEvent
data class Solved(val path: List<Cell>) : SolveEvent

/** BFS from end over open passages: towardEnd[c] is the neighbor one step closer to end. */
private fun towardEndMap(grid: Grid, end: Cell): Map<Cell, Cell> {
    val towardEnd = HashMap<Cell, Cell>()
    val visited = hashSetOf(end)
    val queue = ArrayDeque<Cell>().apply { add(end) }
    while (queue.isNotEmpty()) {
        val cur = queue.removeFirst()
        for (n in grid.openNeighbors(cur)) {
            if (visited.add(n)) {
                towardEnd[n] = cur
                queue.add(n)
            }
        }
    }
    return towardEnd
}

private fun truePathCells(start: Cell, towardEnd: Map<Cell, Cell>): Set<Cell> {
    val onPath = HashSet<Cell>()
    var c: Cell? = start
    while (c != null) {
        onPath.add(c)
        c = towardEnd[c]
    }
    return onPath
}

/**
 * Depth-limited walk from n (never back through c), out to `lookahead` cells from c
 * (n itself is distance 1). Returns (deadEnd, finishInSight):
 * - deadEnd: the walk is fully exhausted with every reached cell at distance <= lookahead
 *   from c, and the branch does not contain end within that walk.
 * - finishInSight: end is reachable from n without going back through c, at distance
 *   <= lookahead from c.
 * lookahead <= 0 disables both: never a dead end, finish never in sight.
 */
internal fun scanBranch(grid: Grid, c: Cell, n: Cell, end: Cell, lookahead: Int): Pair<Boolean, Boolean> {
    if (lookahead <= 0) return false to false
    if (n == end) return false to true
    val visited = hashSetOf(c, n)
    var frontier: Set<Cell> = setOf(n)
    var finishInSight = false
    repeat(lookahead - 1) {
        val nextFrontier = HashSet<Cell>()
        for (cell in frontier) {
            for (nb in grid.openNeighbors(cell)) {
                if (!visited.add(nb)) continue
                if (nb == end) finishInSight = true
                nextFrontier.add(nb)
            }
        }
        frontier = nextFrontier
        if (frontier.isEmpty()) return !finishInSight to finishInSight
    }
    // frontier now holds the cells exactly `lookahead` steps from c; if any still has an
    // unexplored neighbor, the branch continues deeper than we can see.
    val deadEnd = !finishInSight && frontier.none { cell -> grid.openNeighbors(cell).any { it !in visited } }
    return deadEnd to finishInSight
}

private fun candidates(grid: Grid, cur: Cell, visited: Set<Cell>, end: Cell, lookahead: Int): List<Cell> =
    grid.openNeighbors(cur).filter { it !in visited && !scanBranch(grid, cur, it, end, lookahead).first }

private fun chooseNext(
    grid: Grid, cur: Cell, candidates: List<Cell>, onPath: Set<Cell>, towardEnd: Map<Cell, Cell>,
    end: Cell, lookahead: Int, rng: Random,
): Cell {
    if (cur !in onPath) return candidates.random(rng)
    val correct = towardEnd[cur]
    if (correct == null || correct !in candidates) return candidates.random(rng)
    if (scanBranch(grid, cur, correct, end, lookahead).second) return correct
    val others = candidates.filter { it != correct }
    if (others.isNotEmpty() && rng.nextDouble() < MISTAKE_CHANCE) return others.random(rng)
    return correct
}

/** DFS that hugs the true route, occasionally detouring down a wrong branch. */
fun solve(grid: Grid, start: Cell, end: Cell, rng: Random, lookahead: Int = DEFAULT_LOOKAHEAD): Iterator<SolveEvent> =
    iterator {
        if (start == end) {
            yield(Solved(listOf(start)))
            return@iterator
        }

        val towardEnd = towardEndMap(grid, end)
        val onPath = truePathCells(start, towardEnd)

        val visited = hashSetOf(start)
        val stack = arrayListOf(start)
        var forkCell: Cell? = null
        var budget = 0

        while (true) {
            val cur = stack.last()
            if (cur == end) {
                yield(Solved(stack.toList()))
                return@iterator
            }

            val options = candidates(grid, cur, visited, end, lookahead)
            if (options.isNotEmpty()) {
                val next = chooseNext(grid, cur, options, onPath, towardEnd, end, lookahead, rng)
                val enteringDetour = forkCell == null && cur in onPath && next !in onPath
                visited.add(next)
                stack.add(next)
                yield(Advance(cur, next))
                if (enteringDetour) {
                    forkCell = cur
                    budget = rng.nextInt(DETOUR_MIN, DETOUR_MAX + 1) - 1
                } else if (forkCell != null) {
                    budget -= 1
                }
            } else {
                if (stack.size == 1) return@iterator
                val abandoned = stack.removeAt(stack.lastIndex)
                yield(Backtrack(abandoned, stack.last()))
                if (forkCell != null) budget -= 1
            }

            if (forkCell != null && budget <= 0) {
                while (stack.last() != forkCell) {
                    val abandoned = stack.removeAt(stack.lastIndex)
                    yield(Backtrack(abandoned, stack.last()))
                }
            }
            if (forkCell != null && stack.last() == forkCell) forkCell = null
        }
    }

private fun distance(a: Cell, b: Cell): Int = abs(a.x - b.x) + abs(a.y - b.y)

/**
 * Depth-first search that skips branches it can see dead-end within [lookahead] and tries
 * the passage nearest the finish first (straight-line distance, ties at random). A wrong
 * branch is followed to its end before it backs up: no detour limit.
 */
fun solveDepthFirst(grid: Grid, start: Cell, end: Cell, rng: Random, lookahead: Int = DEFAULT_LOOKAHEAD): Iterator<SolveEvent> =
    iterator {
        if (start == end) {
            yield(Solved(listOf(start)))
            return@iterator
        }
        val visited = hashSetOf(start)
        val stack = arrayListOf(start)
        while (true) {
            val cur = stack.last()
            if (cur == end) {
                yield(Solved(stack.toList()))
                return@iterator
            }
            val options = candidates(grid, cur, visited, end, lookahead)
            if (options.isNotEmpty()) {
                val best = options.minOf { distance(it, end) }
                val next = options.filter { distance(it, end) == best }.random(rng)
                visited.add(next)
                stack.add(next)
                yield(Advance(cur, next))
            } else {
                if (stack.size == 1) return@iterator
                val abandoned = stack.removeAt(stack.lastIndex)
                yield(Backtrack(abandoned, stack.last()))
            }
        }
    }

private val CLOCKWISE = intArrayOf(N, E, S, W)

/**
 * Keeps its left hand on the wall: at each cell it tries left, straight, right, then back,
 * relative to the way it is facing. It starts facing the first open passage in the order
 * N, E, S, W. On a perfect maze, stepping back to the previous cell of the route is a
 * backtrack. It ignores the look-ahead.
 */
fun solveWallFollower(grid: Grid, start: Cell, end: Cell): Iterator<SolveEvent> =
    iterator {
        if (start == end) {
            yield(Solved(listOf(start)))
            return@iterator
        }
        var heading = CLOCKWISE.firstOrNull { grid.openDirs(start) and it != 0 } ?: return@iterator
        val stack = arrayListOf(start)
        var cur = start
        // A tree walk crosses each passage at most twice; this bound only stops a runaway
        // on a grid that is not a perfect maze.
        for (move in 0 until 4 * grid.cols * grid.rows) {
            val i = CLOCKWISE.indexOf(heading)
            val d = intArrayOf(-1, 0, 1, 2).map { CLOCKWISE[(i + it + 4) % 4] }
                .first { grid.openDirs(cur) and it != 0 }
            heading = d
            val next = cur.step(d)
            if (stack.size >= 2 && stack[stack.size - 2] == next) {
                stack.removeAt(stack.lastIndex)
                yield(Backtrack(cur, next))
            } else {
                stack.add(next)
                yield(Advance(cur, next))
            }
            cur = next
            if (cur == end) {
                yield(Solved(stack.toList()))
                return@iterator
            }
        }
    }

/** Walks the shortest route with no wrong turns. It ignores the look-ahead. */
fun solvePerfect(grid: Grid, start: Cell, end: Cell): Iterator<SolveEvent> =
    iterator {
        if (start == end) {
            yield(Solved(listOf(start)))
            return@iterator
        }
        val towardEnd = towardEndMap(grid, end)
        if (start !in towardEnd) return@iterator
        val path = arrayListOf(start)
        while (path.last() != end) {
            val next = towardEnd.getValue(path.last())
            yield(Advance(path.last(), next))
            path.add(next)
        }
        yield(Solved(path.toList()))
    }

const val DEFAULT_SOLVER = "human"
val SOLVER_LABELS: Map<String, String> = linkedMapOf(
    "human" to "Human-like", "dfs" to "Depth-first", "wall" to "Wall follower", "perfect" to "Perfect",
)

/** The solver called [name] (a SOLVER_LABELS key); an unknown name uses Human-like. */
fun solveWith(name: String, grid: Grid, start: Cell, end: Cell, rng: Random, lookahead: Int = DEFAULT_LOOKAHEAD): Iterator<SolveEvent> =
    when (name) {
        "dfs" -> solveDepthFirst(grid, start, end, rng, lookahead)
        "wall" -> solveWallFollower(grid, start, end)
        "perfect" -> solvePerfect(grid, start, end)
        else -> solve(grid, start, end, rng, lookahead)
    }
