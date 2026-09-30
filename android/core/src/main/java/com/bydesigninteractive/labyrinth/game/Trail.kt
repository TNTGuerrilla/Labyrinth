// The dot's trail on a perfect maze, ported from maze_game/trail.py.
//
// Because the maze is a tree there is exactly one route from the start to the dot. Edges
// on that route are bright; edges walked and then backed out of are dim.
package com.bydesigninteractive.labyrinth.game

import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Edge
import com.bydesigninteractive.labyrinth.maze.edgeKey

/** What one Trail.move changed, so it can be taken back. */
data class TrailStep(val popped: Boolean, val old: Boolean?)

class Trail(start: Cell) {
    val route = arrayListOf(start)
    val edges = HashMap<Edge, Boolean>()

    val cell: Cell get() = route.last()

    fun move(a: Cell, b: Cell): TrailStep {
        require(a == route.last()) { "move from $a but the trail is at ${route.last()}" }
        val key = edgeKey(a, b)
        val old = edges[key]
        return if (route.size >= 2 && route[route.size - 2] == b) {
            route.removeAt(route.lastIndex)
            edges[key] = false
            TrailStep(true, old)
        } else {
            route.add(b)
            edges[key] = true
            TrailStep(false, old)
        }
    }

    /** Takes back the latest move(a, b), which returned [step]. */
    fun undo(a: Cell, b: Cell, step: TrailStep) {
        require(route.last() == b) { "undo of $a -> $b but the trail is at ${route.last()}" }
        if (step.popped) route.add(a) else route.removeAt(route.lastIndex)
        val key = edgeKey(a, b)
        if (step.old == null) edges.remove(key) else edges[key] = step.old
    }
}
