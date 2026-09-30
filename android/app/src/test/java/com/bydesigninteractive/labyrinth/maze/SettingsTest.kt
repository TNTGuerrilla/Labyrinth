package com.bydesigninteractive.labyrinth.maze

import org.junit.Assert.assertEquals
import org.junit.Test

class SettingsTest {
    @Test
    fun missingValuesGiveDefaults() {
        assertEquals(Settings(), settingsFrom(emptyMap()))
        assertEquals(Settings(), settingsFrom(Field.entries.associateWith { null }))
    }

    @Test
    fun badValuesFallBackPerKey() {
        val s = settingsFrom(mapOf(Field.GEN_SPEED to 2000.0, Field.SOLVE_SPEED to 30.0, Field.LOOKAHEAD to 2.5))
        assertEquals(Settings().genSpeed, s.genSpeed, 0.0)
        assertEquals(30.0, s.solveSpeed, 0.0)
        assertEquals(Settings().lookahead, s.lookahead)
    }

    @Test
    fun minGreaterThanMaxIsSwapped() {
        val s = settingsFrom(mapOf(Field.MIN_CELLS to 50.0, Field.MAX_CELLS to 20.0))
        assertEquals(20, s.minCells)
        assertEquals(50, s.maxCells)
    }

    @Test
    fun boundsAreInclusive() {
        val s = settingsFrom(mapOf(Field.LOOKAHEAD to 12.0, Field.MAX_LEADS to 16.0, Field.HOLD_SECONDS to 0.0))
        assertEquals(12, s.lookahead)
        assertEquals(16, s.maxLeads)
        assertEquals(0.0, s.holdSeconds, 0.0)
    }

    @Test
    fun coverageDefaultsTo100AndStaysIn50To100() {
        assertEquals(100, Settings().coverage)
        assertEquals("Screen coverage (%)", Field.COVERAGE.label)
        assertEquals(5.0, Field.COVERAGE.increment, 0.0)
        assertEquals(Field.MAX_LEADS.ordinal + 1, Field.COVERAGE.ordinal)
        assertEquals(50, settingsFrom(mapOf(Field.COVERAGE to 50.0)).coverage)
        assertEquals(100, settingsFrom(mapOf(Field.COVERAGE to 100.0)).coverage)
        for (bad in listOf(45.0, 105.0, 52.5)) {
            assertEquals(null, Field.COVERAGE.validate(bad))
            assertEquals(100, settingsFrom(mapOf(Field.COVERAGE to bad)).coverage)
        }
    }

    @Test
    fun formatDropsTrailingZero() {
        assertEquals("60", Field.GEN_SPEED.format(60.0))
        assertEquals("4.5", Field.HOLD_SECONDS.format(4.5))
    }

    @Test
    fun solverDefaultsToHumanLikeAndKeepsKnownNames() {
        assertEquals("human", Settings().solver)
        for (name in listOf("human", "dfs", "wall", "perfect")) assertEquals(name, solverFrom(name))
    }

    @Test
    fun unknownOrMissingSolverFallsBack() {
        assertEquals("human", solverFrom(null))
        assertEquals("human", solverFrom(""))
        assertEquals("human", solverFrom("fast"))
    }

    @Test
    fun nextSolverCyclesInLabelOrder() {
        assertEquals("dfs", nextSolver("human", 1))
        assertEquals("perfect", nextSolver("human", -1))
        assertEquals("human", nextSolver("perfect", 1))
        assertEquals("dfs", nextSolver("nope", 1)) // an unknown value counts as human
    }

    @Test
    fun lookaheadLabelNamesTheSolversThatUseIt() {
        assertEquals("Look-ahead (cells, Human-like and Depth-first)", Field.LOOKAHEAD.label)
    }
}
