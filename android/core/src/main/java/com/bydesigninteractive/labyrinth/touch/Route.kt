// Where a tap or a drag may send the dot. The mazes are perfect, so there is one path between
// any two cells. The dot may walk it through cells it has visited, then on into unvisited cells
// that are not forks; the first unvisited fork may end the route but is never passed, so the
// player still chooses every fork and "cells explored" means the same as with the other controls.
package com.bydesigninteractive.labyrinth.touch

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Grid

/** The path from [from] to [to], both included; empty when they are not connected. */
fun uniquePath(grid: Grid, from: Cell, to: Cell): List<Cell> {
    if (from == to) return listOf(from)
    val cameFrom = HashMap<Cell, Cell>()
    val queue = ArrayDeque(listOf(from))
    val seen = hashSetOf(from)
    while (queue.isNotEmpty()) {
        val cell = queue.removeFirst()
        if (cell == to) break
        for (next in grid.openNeighbors(cell)) {
            if (seen.add(next)) {
                cameFrom[next] = cell
                queue.addLast(next)
            }
        }
    }
    if (to !in seen) return emptyList()
    val path = ArrayList<Cell>()
    var cell: Cell? = to
    while (cell != null) {
        path.add(cell)
        cell = cameFrom[cell]
    }
    return path.asReversed()
}

/** How much of [path] the dot may walk: all of it up to and including the first unvisited fork. */
fun allowedPrefix(grid: Grid, path: List<Cell>, visited: Set<Cell>): List<Cell> {
    if (path.isEmpty()) return path
    val allowed = arrayListOf(path[0]) // the dot is already there, or already heading there
    // If the first cell is an unvisited fork, stop there
    if (path[0] !in visited && grid.openNeighbors(path[0]).size >= 3) return allowed
    for (cell in path.drop(1)) {
        allowed.add(cell)
        if (cell !in visited && grid.openNeighbors(cell).size >= 3) break
    }
    return allowed
}

/** The route for a tap on [to], or null when the whole route is not allowed. */
fun tapRoute(grid: Grid, visited: Set<Cell>, from: Cell, to: Cell): List<Cell>? {
    val path = uniquePath(grid, from, to)
    if (path.isEmpty()) return null
    return if (allowedPrefix(grid, path, visited).size == path.size) path else null
}
