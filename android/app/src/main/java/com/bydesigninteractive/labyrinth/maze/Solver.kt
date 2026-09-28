// Human-like maze solver, ported from maze_saver/solver.py.
//
// The dot walks a DFS stack like a person tracing a maze with a finger. It can see a
// short distance down each branch (`lookahead` cells from the fork) and will not wander
// into a branch that visibly dead-ends within that distance. At a fork on the true route
// it always takes the correct turn if it can see the finish down that branch; otherwise
// it usually takes the correct turn, but sometimes (MISTAKE_CHANCE) takes a wrong one
// anyway and wanders for a while before giving up and backing out, bounded by a random
// detour budget (DETOUR_MIN..DETOUR_MAX steps).
package com.bydesigninteractive.labyrinth.maze

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
