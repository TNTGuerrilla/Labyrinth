package io.github.tntguerrilla.mazesaver.maze

import org.junit.Assert.assertEquals
import kotlin.random.Random

fun bfsPath(grid: Grid, start: Cell, end: Cell): List<Cell> {
    val parent = HashMap<Cell, Cell?>().apply { put(start, null) }
    val queue = ArrayDeque<Cell>().apply { add(start) }
    while (queue.isNotEmpty()) {
        val cell = queue.removeFirst()
        if (cell == end) break
        for (n in grid.openNeighbors(cell)) {
            if (n !in parent) {
                parent[n] = cell
                queue.add(n)
            }
        }
    }
    val path = arrayListOf(end)
    while (parent[path.last()] != null) path.add(parent[path.last()]!!)
    return path.reversed()
}

/** Spanning tree check: n-1 passages and everything reachable means no loops. */
fun assertPerfect(grid: Grid) {
    val total = grid.cols * grid.rows
    assertEquals(total - 1, grid.passageCount())
    val seen = hashSetOf(Cell(0, 0))
    val queue = ArrayDeque<Cell>().apply { add(Cell(0, 0)) }
    while (queue.isNotEmpty()) {
        for (n in grid.openNeighbors(queue.removeFirst())) if (seen.add(n)) queue.add(n)
    }
    assertEquals(total, seen.size)
}

fun makeMaze(cols: Int, rows: Int, seed: Int): Grid {
    val g = Grid(cols, rows)
    singleSnake(g, Random(seed)).forEach { }
    return g
}

fun <T> Iterator<T>.toList(): List<T> = asSequence().toList()
