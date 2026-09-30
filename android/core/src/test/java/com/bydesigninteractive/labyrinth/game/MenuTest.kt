package com.bydesigninteractive.labyrinth.game

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

private val S = GameSettings()

private fun MenuModel.press(vararg keys: MenuKey, s: GameSettings = S, now: Double = 0.0): MenuEffect {
    var last: MenuEffect = MenuEffect.None
    for (k in keys) last = key(k, s, now)
    return last
}

class MenuTest {
    @Test
    fun firstOpenIsPlayResume() {
        val m = MenuModel()
        m.open(0.0)
        assertTrue(m.isOpen)
        assertEquals(Tab.PLAY, m.tab)
        assertEquals(Row.Action(MenuAction.RESUME), m.selectedRow(S))
    }

    @Test
    fun firstGameOfASessionOpensOnControls() {
        val m = MenuModel()
        m.open(0.0, first = Tab.CONTROLS)
        assertEquals(Tab.CONTROLS, m.tab)
        assertNull(m.selectedRow(S))
        assertEquals(MenuEffect.None, m.press(MenuKey.OK))
        assertTrue(m.isOpen)
    }

    @Test
    fun tabsWrapAround() {
        val m = MenuModel()
        m.open(0.0, first = Tab.CONTROLS)
        m.press(MenuKey.LEFT)
        assertEquals(Tab.LOOK, m.tab)
        m.press(MenuKey.RIGHT)
        assertEquals(Tab.CONTROLS, m.tab)
    }

    @Test
    fun reopeningWithinAMinuteKeepsTheTabAndRow() {
        val m = MenuModel()
        m.open(0.0)
        m.press(MenuKey.RIGHT, MenuKey.DOWN) // Maze tab, second row
        m.close(10.0)
        m.open(50.0)
        assertEquals(Tab.MAZE, m.tab)
        assertEquals(1, m.selectedIndex(S))
    }

    @Test
    fun afterAMinuteItReopensOnPlayResumeButTabsKeepTheirRows() {
        val m = MenuModel()
        m.open(0.0)
        m.press(MenuKey.DOWN, MenuKey.DOWN) // Play: Auto-solve
        m.press(MenuKey.RIGHT, MenuKey.DOWN) // Maze: second row
        m.close(10.0)
        m.open(70.5)
        assertEquals(Tab.PLAY, m.tab)
        assertEquals(0, m.selectedIndex(S))
        m.press(MenuKey.RIGHT)
        assertEquals(1, m.selectedIndex(S))
    }

    @Test
    fun openAtResumeAlwaysLandsOnResume() {
        val m = MenuModel()
        m.open(0.0)
        m.press(MenuKey.RIGHT, MenuKey.RIGHT)
        m.close(1.0)
        m.openAtResume()
        assertEquals(Tab.PLAY, m.tab)
        assertEquals(0, m.selectedIndex(S))
    }

    @Test
    fun anActionClosesTheMenuAndRuns() {
        val m = MenuModel()
        m.open(0.0)
        m.press(MenuKey.DOWN)
        assertEquals(MenuEffect.Run(MenuAction.HINT), m.press(MenuKey.OK))
        assertFalse(m.isOpen)
    }

    @Test
    fun okOnAToggleFlipsIt() {
        val m = MenuModel()
        m.open(0.0, first = Tab.LOOK)
        assertEquals(MenuEffect.Changed(S.copy(multicolor = false)), m.press(MenuKey.OK))
        assertFalse(m.editing)
    }

    @Test
    fun okOnANumberEditsItWithLeftAndRight() {
        val m = MenuModel()
        m.open(0.0, first = Tab.MOVEMENT)
        assertEquals(MenuEffect.None, m.press(MenuKey.OK))
        assertTrue(m.editing)
        assertEquals(MenuEffect.Changed(S.copy(glideSpeed = 6.0)), m.press(MenuKey.RIGHT))
        assertEquals(Tab.MOVEMENT, m.tab)
        m.press(MenuKey.DOWN)
        assertEquals(0, m.selectedIndex(S)) // up and down do nothing while editing
        m.press(MenuKey.OK)
        assertFalse(m.editing)
    }

    @Test
    fun heldArrowsSpeedUpEditing() {
        val m = MenuModel()
        m.open(0.0, first = Tab.MOVEMENT)
        m.press(MenuKey.OK)
        assertEquals(MenuEffect.Changed(S.copy(glideSpeed = 10.0)), m.key(MenuKey.RIGHT, S, 0.0, repeatCount = 8))
    }

    @Test
    fun backLeavesEditingThenCloses() {
        val m = MenuModel()
        m.open(0.0, first = Tab.MOVEMENT)
        m.press(MenuKey.OK)
        assertEquals(MenuEffect.None, m.press(MenuKey.BACK))
        assertTrue(m.isOpen)
        assertEquals(MenuEffect.Closed, m.press(MenuKey.BACK))
        assertFalse(m.isOpen)
    }

    @Test
    fun pauseAtForksOnlyShowsWithoutBendAssist() {
        assertFalse(rows(Tab.ASSISTS, S).contains(Row.Setting(GameField.PAUSE_AT_FORKS)))
        assertTrue(rows(Tab.ASSISTS, S.copy(followBends = false)).contains(Row.Setting(GameField.PAUSE_AT_FORKS)))
    }

    @Test
    fun customBoundsOnlyShowForCustomSize() {
        assertFalse(rows(Tab.MAZE, S).contains(Row.Setting(GameField.CUSTOM_MIN)))
        val custom = rows(Tab.MAZE, S.copy(size = "custom"))
        assertEquals(Row.Setting(GameField.CUSTOM_MIN), custom[1])
        assertEquals(Row.Setting(GameField.CUSTOM_MAX), custom[2])
    }

    @Test
    fun selectionClampsWhenARowDisappears() {
        val off = S.copy(followBends = false)
        val m = MenuModel()
        m.open(0.0, first = Tab.ASSISTS)
        repeat(10) { m.key(MenuKey.DOWN, off, 0.0) }
        assertEquals(4, m.selectedIndex(off))
        assertEquals(3, m.selectedIndex(S))
    }

    @Test
    fun controlsTabExplainsTheControls() {
        assertTrue(rows(Tab.CONTROLS, S).all { it is Row.Text })
        assertEquals(CONTROLS_TEXT.size, rows(Tab.CONTROLS, S).size)
    }

    @Test
    fun sizeAndCoverageChangesNeedANewMaze() {
        assertTrue(needsNewMaze(S, S.copy(size = "large")))
        assertFalse(needsNewMaze(S, S.copy(customMin = 30)))
        assertTrue(needsNewMaze(S.copy(size = "custom"), S.copy(size = "custom", customMax = 50)))
        assertFalse(needsNewMaze(S, S.copy(glideSpeed = 9.0, maxLeads = 3)))
        assertTrue(needsNewMaze(S, S.copy(coverage = 75)))
        assertFalse(needsNewMaze(S, S.copy(zoomSteps = 3)))
    }

    @Test
    fun lookOffersColorsGridStrengthCoverageAndZoom() {
        assertEquals(
            listOf(
                GameField.MULTICOLOR, GameField.SHOW_GRID, GameField.GRID_STRENGTH, GameField.COVERAGE, GameField.ZOOM,
            ).map { Row.Setting(it) },
            rows(Tab.LOOK, S),
        )
    }

    @Test
    fun lookHidesGridStrengthWhileTheGridIsOff() {
        assertEquals(
            listOf(GameField.MULTICOLOR, GameField.SHOW_GRID, GameField.COVERAGE, GameField.ZOOM).map { Row.Setting(it) },
            rows(Tab.LOOK, S.copy(showGrid = false)),
        )
    }

    @Test
    fun movementOffersTheRemoteTestAndExplainsTheLag() {
        val rows = rows(Tab.MOVEMENT, S)
        assertEquals(Row.Action(MenuAction.TEST_REMOTE), rows[2])
        assertEquals(Row.Text(LAG_NOTE), rows[3])
        assertEquals(
            "Your remote's lag is added to the pause at forks, and a turn pressed up to that late still counts. " +
                "Test again if you change remotes or the TV's picture mode.",
            LAG_NOTE,
        )
    }

    @Test
    fun playDoesNotListTheRemoteTest() {
        assertFalse(rows(Tab.PLAY, S).contains(Row.Action(MenuAction.TEST_REMOTE)))
        assertEquals(PLAY_ACTIONS.map { Row.Action(it) }, rows(Tab.PLAY, S))
    }

    @Test
    fun theRemoteTestRowRunsLikeAnAction() {
        val m = MenuModel()
        m.open(0.0, first = Tab.MOVEMENT)
        m.press(MenuKey.DOWN, MenuKey.DOWN)
        assertEquals(MenuEffect.Run(MenuAction.TEST_REMOTE), m.press(MenuKey.OK))
    }
}
