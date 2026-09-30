// Route finding for hints, the shortest route length and auto-solve, ported from
// maze_game/assist.py.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Grid

/**
 * True if the branch entered from [frm] into [n] visibly ends within [depth] cells of frm
 * (n is 1) without containing [end]. depth <= 0 never hides a branch.
 */
fun deadEndWithin(grid: Grid, frm: Cell, n: Cell, end: Cell, depth: Int): Boolean {
    if (depth <= 0) return false
    val seen = hashSetOf(frm, n)
    var frontier = listOf(n)
    var dist = 1
    while (frontier.isNotEmpty()) {
        if (end in frontier) return false
        val next = frontier.flatMap { grid.openNeighbors(it) }.filter { it !in seen }
        if (dist >= depth) return next.isEmpty()
        seen.addAll(next)
        frontier = next
        dist++
    }
    return true
}

/** BFS from end over open passages: result[c] is the neighbor one step closer to end. */
fun buildTowardEnd(grid: Grid, end: Cell): Map<Cell, Cell> {
    val parents = HashMap<Cell, Cell>()
    val visited = hashSetOf(end)
    val queue = ArrayDeque<Cell>().apply { add(end) }
    while (queue.isNotEmpty()) {
        val cur = queue.removeFirst()
        for (n in grid.openNeighbors(cur)) {
            if (visited.add(n)) {
                parents[n] = cur
                queue.add(n)
            }
        }
    }
    return parents
}
