package com.bydesigninteractive.labyrinth.mobile

import com.bydesigninteractive.labyrinth.game.GameField
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.Kind
import com.bydesigninteractive.labyrinth.game.MenuAction
import com.bydesigninteractive.labyrinth.touch.Hold
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PhoneMenuTest {
    private val s = GameSettings()
    private val p = PhoneSettings()

    private fun fields(tab: PhoneTab, game: GameSettings = s) =
        phoneRows(tab, game, p, "1.0.0").filterIsInstance<MenuRow.Game>().map { it.field }

    @Test
    fun tabsComeInTheSpecsOrder() {
        assertEquals(
            listOf("Controls", "Play", "Maze", "Assists", "Movement", "Look", "About"),
            PhoneTab.entries.map { it.title },
        )
    }

    @Test
    fun controlsStartWithTheTouchChoiceAndItsHelp() {
        val rows = phoneRows(PhoneTab.CONTROLS, s, p, "1.0.0")
        assertEquals(MenuRow.Choice(PhoneChoice.TOUCH), rows[0])
        assertEquals(MenuRow.Note(TouchScheme.SWIPE.help), rows[1])
        assertEquals(KEY_HELP.map { MenuRow.Note(it) }, rows.drop(2))
    }

    @Test
    fun playHasTheSixActions() {
        assertEquals(
            listOf(MenuAction.RESUME, MenuAction.HINT, MenuAction.AUTO_SOLVE, MenuAction.FLASH, MenuAction.REPLAY, MenuAction.NEW_MAZE),
            phoneRows(PhoneTab.PLAY, s, p, "1.0.0").map { (it as MenuRow.Action).action },
        )
    }

    @Test
    fun customSizesAppearOnlyForCustom() {
        assertFalse(GameField.CUSTOM_MIN in fields(PhoneTab.MAZE))
        val custom = fields(PhoneTab.MAZE, s.copy(size = "custom"))
        assertEquals(listOf(GameField.SIZE, GameField.CUSTOM_MIN, GameField.CUSTOM_MAX), custom.take(3))
        assertEquals(MenuRow.Note(SIZE_NOTE), phoneRows(PhoneTab.MAZE, s, p, "1.0.0").last())
    }

    @Test
    fun pauseAtForksShowsOnlyForHoldToMove() {
        assertFalse(GameField.PAUSE_AT_FORKS in fields(PhoneTab.ASSISTS))
        assertTrue(GameField.PAUSE_AT_FORKS in fields(PhoneTab.ASSISTS, s.copy(followBends = false)))
        assertFalse(GameField.PAUSE_AT_FORKS in fields(PhoneTab.ASSISTS, s.copy(followBends = false, runStraight = true)))
        for (game in listOf(s, s.copy(followBends = false), s.copy(followBends = false, runStraight = true))) {
            val f = fields(PhoneTab.ASSISTS, game)
            assertEquals(GameField.STEERING, f[0])
            assertFalse(GameField.FOLLOW_BENDS in f)
            assertFalse(GameField.RUN_STRAIGHT in f)
        }
        assertTrue("Steering" in BENDS_NOTE)
        assertFalse("Bend assist off" in BENDS_NOTE)
        assertEquals(MenuRow.Note(BENDS_NOTE), phoneRows(PhoneTab.ASSISTS, s, p, "1.0.0").last())
    }

    @Test
    fun movementHasNoRemoteTest() {
        assertEquals(
            listOf(MenuRow.Game(GameField.GLIDE_SPEED), MenuRow.Game(GameField.TURN_PAUSE)),
            phoneRows(PhoneTab.MOVEMENT, s, p, "1.0.0"),
        )
    }

    @Test
    fun lookEndsWithOrientationAndSystemBars() {
        val rows = phoneRows(PhoneTab.LOOK, s, p, "1.0.0")
        assertEquals(listOf(MenuRow.Choice(PhoneChoice.ORIENTATION), MenuRow.Toggle(PhoneToggle.HIDE_BARS)), rows.takeLast(2))
        assertTrue(GameField.GRID_STRENGTH in fields(PhoneTab.LOOK))
        assertFalse(GameField.GRID_STRENGTH in fields(PhoneTab.LOOK, s.copy(showGrid = false)))
    }

    @Test
    fun aboutShowsTheVersionUpdatesHowToPlayAndLicense() {
        assertEquals(
            listOf(
                MenuRow.Note("Labyrinth Mobile 1.2.3"), MenuRow.Status,
                MenuRow.Link(MenuLink.CHECK_NOW), MenuRow.Link(MenuLink.WHATS_NEW), MenuRow.Toggle(PhoneToggle.CHECK_UPDATES),
                MenuRow.Link(MenuLink.HOW_TO_PLAY),
                MenuRow.Note(COPYRIGHT), MenuRow.Note(LICENSE_LINE), MenuRow.Note(PROJECT_ADDRESS),
            ),
            phoneRows(PhoneTab.ABOUT, s, p, "1.2.3"),
        )
    }

    @Test
    fun anOfferedUpdateAddsUpdateAndDismiss() {
        val rows = phoneRows(PhoneTab.ABOUT, s, p, "1.2.3", canUpdate = true)
        assertEquals(listOf(MenuRow.Link(MenuLink.UPDATE), MenuRow.Link(MenuLink.DISMISS)), rows.subList(2, 4))
    }

    @Test
    fun theMenuReopensWhereItClosedWithinAMinute() {
        assertEquals(PhoneTab.PLAY, reopenTab(PhoneTab.LOOK, null, 100.0))
        assertEquals(PhoneTab.LOOK, reopenTab(PhoneTab.LOOK, 50.0, 100.0))
        assertEquals(PhoneTab.PLAY, reopenTab(PhoneTab.LOOK, 30.0, 100.0))
    }

    @Test
    fun everySliderStepIsAValidValueAndMapsBack() {
        for (f in GameField.entries.filter { it.kind == Kind.NUMBER }) {
            for (step in 0..sliderSteps(f)) {
                val v = sliderValue(f, step)
                assertNotNull("${f.name} step $step gave $v", f.validate(v))
                assertEquals("${f.name} step $step", step, sliderStep(f, v))
            }
        }
        assertEquals(20, sliderSteps(GameField.TURN_PAUSE))
        assertEquals(0.2, sliderValue(GameField.TURN_PAUSE, 4), 1e-12)
        assertEquals(199, sliderSteps(GameField.GEN_SPEED))
    }

    @Test
    fun customMinAndMaxStayInOrder() {
        val custom = s.copy(size = "custom", customMin = 20, customMax = 40)
        assertEquals(50 to 50, setNumber(custom, GameField.CUSTOM_MIN, 50.0).let { it.customMin to it.customMax })
        assertEquals(10 to 10, setNumber(custom, GameField.CUSTOM_MAX, 10.0).let { it.customMin to it.customMax })
        assertEquals(12, setNumber(s, GameField.LOOKAHEAD, 99.0).lookahead)
    }

    @Test
    fun choicesReadAndSetThePhoneSettings() {
        assertEquals(listOf("Swipe", "Drag", "Joystick", "Tap to go"), choiceOptions(PhoneChoice.TOUCH))
        assertEquals(listOf("Auto", "Portrait", "Landscape"), choiceOptions(PhoneChoice.ORIENTATION))
        assertEquals(0, choiceIndex(PhoneChoice.ORIENTATION, p))
        val landscape = choose(PhoneChoice.ORIENTATION, p, 2)
        assertEquals(Hold.LANDSCAPE, landscape.hold)
        assertEquals(2, choiceIndex(PhoneChoice.ORIENTATION, landscape))
        assertTrue(toggleValue(PhoneToggle.HIDE_BARS, p))
        assertFalse(flip(PhoneToggle.HIDE_BARS, p).hideBars)
    }

    @Test
    fun storedPhoneSettingsFallBackToDefaults() {
        assertEquals(PhoneSettings(), phoneSettingsFrom(null, null, null))
        assertEquals(PhoneSettings(), phoneSettingsFrom("NOPE", "sideways", null))
        assertEquals(
            PhoneSettings(TouchScheme.TAP, Hold.PORTRAIT, false, Hand.LEFT),
            phoneSettingsFrom("TAP", "PORTRAIT", false, "LEFT"),
        )
        assertEquals(false, phoneSettingsFrom(null, null, null, null, false).showTrace)
        assertEquals(true, phoneSettingsFrom(null, null, null).showTrace)
    }

    @Test
    fun showTracedPathShowsOnlyForDrag() {
        val toggle = MenuRow.Toggle(PhoneToggle.SHOW_TRACE)
        assertFalse(toggle in phoneRows(PhoneTab.CONTROLS, s, p, "1.0.0"))
        val drag = p.copy(touch = TouchScheme.DRAG)
        assertEquals(listOf(MenuRow.Choice(PhoneChoice.TOUCH), toggle), phoneRows(PhoneTab.CONTROLS, s, drag, "1.0.0").take(2))
        assertTrue(toggleValue(PhoneToggle.SHOW_TRACE, drag))
        assertFalse(flip(PhoneToggle.SHOW_TRACE, drag).showTrace)
    }

    @Test
    fun joystickHandShowsOnlyForTheJoystick() {
        assertFalse(MenuRow.Choice(PhoneChoice.JOYSTICK_HAND) in phoneRows(PhoneTab.CONTROLS, s, p, "1.0.0"))
        val joystick = p.copy(touch = TouchScheme.JOYSTICK)
        val rows = phoneRows(PhoneTab.CONTROLS, s, joystick, "1.0.0")
        assertEquals(listOf(MenuRow.Choice(PhoneChoice.TOUCH), MenuRow.Choice(PhoneChoice.JOYSTICK_HAND)), rows.take(2))
        assertEquals(listOf("Left", "Right"), choiceOptions(PhoneChoice.JOYSTICK_HAND))
        assertEquals(1, choiceIndex(PhoneChoice.JOYSTICK_HAND, joystick))
        assertEquals(Hand.LEFT, choose(PhoneChoice.JOYSTICK_HAND, joystick, 0).hand)
    }

    @Test
    fun theControllerTestAppearsOnceAControllerWasUsed() {
        val link = MenuRow.Link(MenuLink.CONTROLLER_TEST)
        assertFalse(link in phoneRows(PhoneTab.CONTROLS, s, p, "1.0.0"))
        assertTrue(link in phoneRows(PhoneTab.CONTROLS, s, p, "1.0.0", controllerUsed = true))
    }

    @Test
    fun everySchemeHasHelp() {
        for (t in TouchScheme.entries) assertTrue(t.help.isNotBlank())
    }

    @Test
    fun howToPlayNamesTheGoalAndTheMenu() {
        val lines = howToPlay(TouchScheme.SWIPE)
        assertTrue(lines.first().contains("green dot"))
        assertTrue(lines.any { it.contains("Menu > Controls") })
    }

    @Test
    fun howToPlayFollowsTheTouchScheme() {
        assertTrue(howToPlay(TouchScheme.JOYSTICK).contains(TouchScheme.JOYSTICK.help))
        assertTrue(howToPlay(TouchScheme.SWIPE).contains(TouchScheme.SWIPE.help))
    }
}
