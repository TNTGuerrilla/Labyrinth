// The app's launcher screen, built for a TV remote: Play, Use as (game and screensaver,
// game only, screensaver only), the screensaver settings, updates and info. Up and down move between rows, left
// and right change the focused value (hold to speed up), and changes save as they are made.
// Also opened from the system screensaver settings, when a TV shows them.
package com.bydesigninteractive.labyrinth

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.StateListDrawable
import android.net.ConnectivityManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings.Secure
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import com.bydesigninteractive.labyrinth.game.Mode
import com.bydesigninteractive.labyrinth.maze.Field
import com.bydesigninteractive.labyrinth.maze.SOLVER_LABELS
import com.bydesigninteractive.labyrinth.maze.Settings
import com.bydesigninteractive.labyrinth.maze.nextSolver
import com.bydesigninteractive.labyrinth.maze.solverFrom
import com.bydesigninteractive.labyrinth.play.GameActivity
import com.bydesigninteractive.labyrinth.play.GameStore
import com.bydesigninteractive.labyrinth.play.RemoteTestActivity
import com.bydesigninteractive.labyrinth.play.Session
import com.bydesigninteractive.labyrinth.update.Release
import com.bydesigninteractive.labyrinth.update.UpdateFailure
import com.bydesigninteractive.labyrinth.update.UpdateStore
import com.bydesigninteractive.labyrinth.update.Updates
import com.bydesigninteractive.labyrinth.update.WhatsNew
import com.bydesigninteractive.labyrinth.update.visibleUpdate
import com.bydesigninteractive.labyrinth.update.withArrivedNotes
import java.io.IOException
import java.net.Inet4Address
import kotlin.concurrent.thread

// Between BACKGROUND and FOCUSED, so the command box shows whether or not the help has focus.
private val CODE_BACKGROUND = Color.rgb(30, 34, 42)

private const val GUIDE_URL = "github.com/TNTGuerrilla/Labyrinth"
private const val BRANDS_URL = "github.com/TNTGuerrilla/Labyrinth#brand-specific-setup"
private const val COPYRIGHT = "\u00a9 2026 ByDesign Interactive"
private const val LICENSE_TEXT = "Licensed under Apache 2.0"
private const val LICENSE_ADDRESS = "github.com/TNTGuerrilla/Labyrinth/blob/master/LICENSE"

class SettingsActivity : Activity() {
    private lateinit var settings: Settings
    private lateinit var mode: Mode
    private lateinit var playButton: TextView
    private lateinit var modeValue: TextView
    private lateinit var solverValue: TextView
    private val screensaverViews = ArrayList<View>()
    private val valueViews = HashMap<Field, TextView>()
    private lateinit var column: LinearLayout
    private lateinit var help: LinearLayout
    private var notesBlock: LinearLayout? = null
    private var notesText: TextView? = null
    private var shownNews: WhatsNew? = null
    private lateinit var updateStatus: TextView
    private lateinit var updateButton: TextView
    private lateinit var dismissButton: TextView
    private lateinit var checkToggle: TextView
    private var offered: Release? = null
    // Check now found this and it stays on offer for the rest of the session, even if weekly
    // checks are off and later automatic checks answer null without asking the network.
    private var sessionOffer: Release? = null
    private var checkingNow = false
    private var downloading = false
    private var installing = false
    private var justShowedInstallFailure = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = SettingsStore.load(this)
        mode = GameStore.mode(this)
        reconcileDream()
        if (intent?.action == Intent.ACTION_MAIN) Session.controlsShown = false

        column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(64), dp(40), dp(64), dp(40))
        }
        column.addView(text("Labyrinth", 26f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(16), 0, dp(16), dp(16))
        })
        val current = Updates.currentVersion(this)
        UpdateStore.startWhatsNew(this, current)?.let { news ->
            showNotes(news)
            UpdateStore.markWhatsNewSeen(this, current) // shown once: it counts as seen
        }
        playButton = button("Play") { play() }
        column.addView(playButton)
        column.addView(modeRow())
        var first: View? = null
        for (field in Field.entries) {
            val row = fieldRow(field)
            column.addView(row)
            screensaverViews.add(row)
            if (first == null) first = row
            if (field == Field.SOLVE_SPEED) column.addView(solverRow().also { screensaverViews.add(it) })
        }
        column.addView(button("Preview screensaver") { startActivity(Intent(this, PreviewActivity::class.java)) }
            .also { screensaverViews.add(it) })
        column.addView(button("Reset to defaults") { update(Settings()) }.also { screensaverViews.add(it) })
        column.addView(text("Info", 20f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(16), dp(24), dp(16), dp(8))
        })
        column.addView(infoLine("Labyrinth ${Updates.currentVersion(this)}", TEXT))
        column.addView(infoLine(COPYRIGHT, DIM_TEXT))
        column.addView(infoRow("GitHub", GUIDE_URL))
        column.addView(infoRow("License", LICENSE_TEXT))
        column.addView(infoLine(LICENSE_ADDRESS, DIM_TEXT))
        updateStatus = text("", 17f, DIM_TEXT).apply { setPadding(dp(16), dp(16), dp(16), dp(4)) }
        column.addView(updateStatus)
        updateButton = button("Update") { startUpdate() }
        column.addView(updateButton)
        dismissButton = button("Dismiss") { dismissUpdate() }
        column.addView(dismissButton)
        column.addView(button("Check now") { checkNow() })
        column.addView(button("What's new") { showNotes(UpdateStore.runningWhatsNew(this, Updates.currentVersion(this)), focus = true) })
        checkToggle = button("") { toggleChecks() }
        column.addView(checkToggle)
        showUpdate(null)
        // Focusable so the remote can scroll down to it: a ScrollView only follows focus.
        help = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(2))
            isFocusable = true
            background = focusBackground()
        }
        column.addView(help)
        screensaverViews.add(help)

        setContentView(ScrollView(this).apply {
            setBackgroundColor(BACKGROUND)
            addView(column)
        })
        refresh()
        applyMode()
        if (mode.game) playButton.requestFocus() else first?.requestFocus()
        if (intent?.getBooleanExtra(Updates.EXTRA_INSTALL_FAILED, false) == true) {
            intent.removeExtra(Updates.EXTRA_INSTALL_FAILED) // not again if the activity is recreated
            if (Updates.takeInstallReport()) showInstallFailed()
        }
    }

    override fun onResume() {
        super.onResume()
        // Refreshed here so the status is current after running the ADB command.
        showSetupHelp()
        // An installer that asked for confirmation while this app was in the background was
        // blocked by Android and reports nothing, so coming back offers Update again.
        installing = false
        if (justShowedInstallFailure) {
            // The failure message is on screen; do not overwrite it right away.
            justShowedInstallFailure = false
        } else if (!downloading) {
            Updates.check(this, force = true, onDone = ::onAutoCheck)
        }
    }

    /**
     * An automatic check (on resume, or after turning checks on) came back. It answers null
     * without asking the network when weekly checks are off, in which case whatever Check now
     * found earlier this session, if anything, stays on offer.
     */
    private fun onAutoCheck(release: Release?) {
        if (isDestroyed) return
        showArrivedNotes()
        if (downloading || checkingNow) return
        showUpdate(release ?: sessionOffer)
    }

    /** The check fetched the notes an open What's new lacked: they replace its fallback in place. */
    private fun showArrivedNotes() {
        val news = shownNews?.let { withArrivedNotes(it, UpdateStore.loadSeen(this).notes) } ?: return
        shownNews = news
        notesText?.let { it.text = styledNotes(news.lines(), it.paint) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        if (intent.action == Intent.ACTION_MAIN) Session.controlsShown = false
        if (intent.getBooleanExtra(Updates.EXTRA_INSTALL_FAILED, false) && Updates.takeInstallReport()) showInstallFailed()
    }

    /**
     * InstallStatusActivity reports that the installer did not install the update. Any app
     * could send this extra, so it is only honored while an install this process committed
     * has not reported back yet, and even then it only shows a message and offers Update again.
     */
    private fun showInstallFailed() {
        installing = false
        // offered is null when this activity was recreated while the installer was open.
        val release = offered ?: visibleUpdate(UpdateStore.load(this), Updates.currentVersion(this))
        showUpdate(release, "The update was not installed.")
        justShowedInstallFailure = true
    }

    /** The update row: what is on offer, or the running version, and the check switch. */
    private fun showUpdate(release: Release?, message: String? = null) {
        offered = release
        val enabled = UpdateStore.enabled(this)
        checkToggle.text = "Check for updates: ${if (enabled) "On" else "Off"}"
        val elsewhere = Updates.isUpdating && !downloading
        updateStatus.text = message
            ?: release?.let { if (elsewhere) "Labyrinth ${it.version} is downloading." else "Labyrinth ${it.version} is available." }
            ?: "Version ${Updates.currentVersion(this)}"
        val visible = release != null && !downloading && !installing && !elsewhere
        if (!visible && (updateButton.isFocused || dismissButton.isFocused)) checkToggle.requestFocus()
        val actions = if (visible) View.VISIBLE else View.GONE
        updateButton.visibility = actions
        dismissButton.visibility = actions
    }

    private fun startUpdate() {
        val release = offered ?: return
        if (!packageManager.canRequestPackageInstalls()) {
            askForInstallPermission(release)
            return
        }
        if (!Updates.beginUpdate()) {
            showUpdate(release)
            return
        }
        downloading = true
        checkToggle.requestFocus()
        showUpdate(release, "Downloading Labyrinth ${release.version}...")
        thread(name = "update-download", isDaemon = true) {
            var nowInstalling = false
            val message = try {
                val downloaded = try {
                    Result.success(Updates.download(this, release) { percent ->
                        runOnUiThread { if (!isDestroyed) updateStatus.text = "Downloading Labyrinth ${release.version}: $percent%" }
                    })
                } catch (e: IOException) {
                    Result.failure(e)
                }
                downloaded.fold(
                    onSuccess = { apk ->
                        try {
                            Updates.install(this, apk)
                            nowInstalling = true
                            "Installing Labyrinth ${release.version}..."
                        } catch (_: Exception) {
                            "The update could not be installed."
                        }
                    },
                    onFailure = { (it as? UpdateFailure)?.message ?: "The download was interrupted." },
                )
            } finally {
                Updates.endUpdate()
            }
            runOnUiThread {
                if (isDestroyed) return@runOnUiThread
                downloading = false
                installing = nowInstalling
                showUpdate(release, message)
            }
        }
    }

    /** Android asks once per app before it lets an app install updates. */
    private fun askForInstallPermission(release: Release) {
        val intent = Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:$packageName"))
        try {
            startActivity(intent)
            showUpdate(release, "Allow Labyrinth to install apps, then come back and select Update again.")
        } catch (_: ActivityNotFoundException) {
            showUpdate(release, "Allow installs from Labyrinth under Settings, Apps, Special app access, " +
                "Install unknown apps, then select Update again.")
        }
    }

    private fun dismissUpdate() {
        val release = offered ?: return
        UpdateStore.edit(this) { it.copy(dismissed = release.version) }
        if (sessionOffer?.version == release.version) sessionOffer = null
        checkToggle.requestFocus()
        showUpdate(null)
    }

    private fun toggleChecks() {
        val enabled = !UpdateStore.enabled(this)
        UpdateStore.setEnabled(this, enabled)
        showUpdate(sessionOffer)
        if (enabled) Updates.check(this, force = true, onDone = ::onAutoCheck)
    }

    /** The user selected Check now: asks GitHub even with checks off, once at a time. */
    private fun checkNow() {
        if (downloading || installing || checkingNow) return
        checkingNow = true
        updateStatus.text = "Checking..."
        Updates.checkNow(this) { outcome ->
            checkingNow = false
            if (isDestroyed || downloading) return@checkNow
            when (outcome) {
                is Updates.CheckOutcome.Available -> {
                    sessionOffer = outcome.release
                    showUpdate(outcome.release)
                }
                Updates.CheckOutcome.UpToDate -> {
                    sessionOffer = null
                    showUpdate(null, "Up to date")
                }
                is Updates.CheckOutcome.Failed -> showUpdate(offered, outcome.message)
            }
        }
    }

    private fun infoLine(value: String, color: Int) =
        text(value, 17f, color).apply { setPadding(dp(16), dp(2), dp(16), dp(2)) }

    private fun infoRow(label: String, value: String) = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        setPadding(dp(16), dp(2), dp(16), dp(2))
        addView(text(label, 17f, TEXT), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        addView(text(value, 17f, DIM_TEXT))
    }

    /** The "Updated to X.Y.Z" block under the title: after an update, or from What's new. */
    private fun showNotes(news: WhatsNew, focus: Boolean = false) {
        notesBlock?.let { column.removeView(it) }
        val block = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(8), dp(16), dp(16))
            isFocusable = true // a ScrollView only follows focus
            background = focusBackground()
        }
        block.addView(text("Updated to ${news.version}", 22f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            setPadding(0, 0, 0, dp(8))
        })
        val notes = text("", 16f, DIM_TEXT)
        notes.text = styledNotes(news.lines(), notes.paint)
        block.addView(notes)
        column.addView(block, 1) // index 0 is the title
        notesBlock = block
        notesText = notes
        shownNews = news
        if (focus) block.requestFocus()
    }

    /** Which solver the screensaver uses, changed with left and right like the other rows. */
    private fun solverRow(): LinearLayout {
        solverValue = text("", 17f, ACCENT).apply {
            gravity = Gravity.END
            typeface = Typeface.MONOSPACE
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(6), dp(16), dp(6))
            isFocusable = true
            background = focusBackground()
            addView(text("Solver", 17f, TEXT), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(solverValue)
            setOnKeyListener { _, keyCode, event ->
                val sign = when (keyCode) {
                    KeyEvent.KEYCODE_DPAD_LEFT -> -1
                    KeyEvent.KEYCODE_DPAD_RIGHT -> 1
                    else -> return@setOnKeyListener false
                }
                if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) {
                    update(settings.copy(solver = nextSolver(settings.solver, sign)))
                }
                true
            }
        }
    }

    /** Use as: game and screensaver / game only / screensaver only, changed with left and right like the other rows. */
    private fun modeRow(): LinearLayout {
        modeValue = text("", 17f, ACCENT).apply {
            gravity = Gravity.END
            typeface = Typeface.MONOSPACE
        }
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(6), dp(16), dp(6))
            isFocusable = true
            background = focusBackground()
            addView(text("Use as", 17f, TEXT), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(modeValue)
            setOnKeyListener { _, keyCode, event ->
                val sign = when (keyCode) {
                    KeyEvent.KEYCODE_DPAD_LEFT -> -1
                    KeyEvent.KEYCODE_DPAD_RIGHT -> 1
                    else -> return@setOnKeyListener false
                }
                if (event.action == KeyEvent.ACTION_DOWN && event.repeatCount == 0) setMode(mode.next(sign))
                true
            }
        }
    }

    /**
     * Turning the screensaver off disables the dream component, so Labyrinth leaves the TV's
     * screensaver list; the TV falls back to its default if Labyrinth was chosen.
     */
    private fun setMode(next: Mode) {
        mode = next
        GameStore.setMode(this, next)
        setDreamEnabled(next.screensaver)
        applyMode()
    }

    private fun setDreamEnabled(on: Boolean) {
        packageManager.setComponentEnabledSetting(
            ComponentName(this, LabyrinthDreamService::class.java),
            if (on) PackageManager.COMPONENT_ENABLED_STATE_DEFAULT
            else PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
            PackageManager.DONT_KILL_APP,
        )
    }

    /** Brings the dream component back in line with the stored mode if they disagree (say, after a reinstall). */
    private fun reconcileDream() {
        val state = packageManager.getComponentEnabledSetting(ComponentName(this, LabyrinthDreamService::class.java))
        // The manifest leaves the dream enabled, so DEFAULT counts as on.
        val on = state == PackageManager.COMPONENT_ENABLED_STATE_DEFAULT ||
            state == PackageManager.COMPONENT_ENABLED_STATE_ENABLED
        if (on != mode.screensaver) setDreamEnabled(mode.screensaver)
    }

    private fun applyMode() {
        modeValue.text = "<  ${mode.label}  >"
        playButton.visibility = if (mode.game) View.VISIBLE else View.GONE
        val saver = if (mode.screensaver) View.VISIBLE else View.GONE
        screensaverViews.forEach { it.visibility = saver }
    }

    private fun fieldRow(field: Field): LinearLayout {
        val value = text("", 17f, ACCENT).apply {
            gravity = Gravity.END
            typeface = Typeface.MONOSPACE
        }
        valueViews[field] = value
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(6), dp(16), dp(6))
            isFocusable = true
            background = focusBackground()
            addView(text(field.label, 17f, TEXT), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(value)
            setOnKeyListener { _, keyCode, event ->
                val sign = when (keyCode) {
                    KeyEvent.KEYCODE_DPAD_LEFT -> -1
                    KeyEvent.KEYCODE_DPAD_RIGHT -> 1
                    else -> return@setOnKeyListener false
                }
                if (event.action == KeyEvent.ACTION_DOWN) adjust(field, sign, event.repeatCount)
                true
            }
        }
    }

    /** Steps the field by its increment, faster the longer the button is held. */
    private fun adjust(field: Field, sign: Int, repeatCount: Int) {
        val multiplier = when {
            repeatCount >= 20 -> 10
            repeatCount >= 8 -> 5
            else -> 1
        }
        val value = (field.get(settings) + sign * field.increment * multiplier).coerceIn(field.low, field.high)
        var next = field.set(settings, value)
        // Keep min <= max by pushing the other bound along.
        if (field == Field.MIN_CELLS && next.minCells > next.maxCells) next = next.copy(maxCells = next.minCells)
        if (field == Field.MAX_CELLS && next.maxCells < next.minCells) next = next.copy(minCells = next.maxCells)
        update(next)
    }

    private fun update(next: Settings) {
        settings = next
        SettingsStore.save(this, next)
        refresh()
    }

    private fun refresh() {
        for ((field, view) in valueViews) view.text = "<  ${field.format(field.get(settings))}  >"
        solverValue.text = "<  ${SOLVER_LABELS.getValue(solverFrom(settings.solver))}  >"
    }

    /**
     * Until the remote test has been finished once, Play offers it first (Back there skips it),
     * then starts the game; after that, straight into a game.
     */
    private fun play() {
        if (GameStore.loadRemote(this) == null) {
            startActivity(Intent(this, RemoteTestActivity::class.java).putExtra(RemoteTestActivity.EXTRA_THEN_START, ComponentName(this, GameActivity::class.java)))
        } else {
            startActivity(Intent(this, GameActivity::class.java))
        }
    }

    private fun button(label: String, onClick: () -> Unit): TextView =
        text(label, 17f, TEXT).apply {
            setPadding(dp(16), dp(8), dp(16), dp(8))
            isFocusable = true
            isClickable = true
            background = focusBackground()
            setOnClickListener { onClick() }
        }

    /**
     * The status line and setup steps under the settings. The commands are written for
     * PowerShell, since a bare `adb` is usually not on a Windows PC's PATH.
     */
    private fun showSetupHelp() {
        val component = "$packageName/.LabyrinthDreamService"
        val active = try {
            Secure.getString(contentResolver, "screensaver_components")?.contains(component) == true
        } catch (_: SecurityException) {
            null
        }
        help.removeAllViews()
        when (active) {
            true -> paragraph("Labyrinth is the current screensaver.", TEXT)
            false -> paragraph("Labyrinth is not the current screensaver yet.", TEXT)
            null -> {}
        }
        paragraph(
            "To make it the screensaver, turn on USB debugging in this TV's Developer options, then run these " +
                "in PowerShell on a PC on the same network. adb comes with Android Studio or Google's SDK " +
                "Platform-Tools; change the first line if yours is somewhere else.",
            DIM_TEXT,
        )
        val ip = tvAddress()
        // TCL's firmware stops background apps, screensavers included, that lack its own
        // AUTO_START permission. Its Auto Launch switch is hard to find, so grant it here.
        val tcl = Build.MANUFACTURER.equals("TCL", ignoreCase = true)
        code(
            *listOfNotNull(
                "\$adb = \"\$env:LOCALAPPDATA\\Android\\Sdk\\platform-tools\\adb.exe\"",
                "& \$adb connect ${ip ?: "<TV IP address>"}:5555",
                "& \$adb shell settings put secure screensaver_components $component",
                if (tcl) "& \$adb shell appops set $packageName AUTO_START allow" else null,
            ).toTypedArray(),
        )
        paragraph(
            buildString {
                if (ip == null) append("Find this TV's IP address under Settings, Network & Internet. ")
                append("After the connect command, choose Always allow on the \"Allow USB debugging?\" prompt on this TV.")
            },
            DIM_TEXT,
        )
        if (tcl) {
            paragraph("The last command is for TCL TVs, which block screensavers from starting unless the app may launch itself.", DIM_TEXT)
        } else {
            paragraph("If the screensaver does not start after the idle timeout, see the brand-specific steps: $BRANDS_URL", DIM_TEXT)
        }
        paragraph("You only need a PC and adb once, for this setup. After that, Labyrinth updates itself from this screen.", DIM_TEXT)
        paragraph("Full setup guide: $GUIDE_URL", DIM_TEXT)
    }

    /** This TV's IPv4 address on its current network, or null if it has none. */
    private fun tvAddress(): String? {
        val connectivity = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = connectivity.activeNetwork ?: return null
        val addresses = connectivity.getLinkProperties(network)?.linkAddresses ?: return null
        return addresses.map { it.address }.firstOrNull { it is Inet4Address && !it.isLoopbackAddress }?.hostAddress
    }

    private fun paragraph(value: String, color: Int) {
        help.addView(text(value, 15f, color).apply { setPadding(0, 0, 0, dp(14)) })
    }

    private fun code(vararg lines: String) {
        help.addView(text(lines.joinToString("\n"), 14f, ACCENT).apply {
            typeface = Typeface.MONOSPACE
            setPadding(dp(12), dp(10), dp(12), dp(10))
            background = GradientDrawable().apply {
                setColor(CODE_BACKGROUND)
                cornerRadius = dp(6).toFloat()
            }
        }, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            bottomMargin = dp(14)
        })
    }

    private fun text(value: String, sizeSp: Float, color: Int) = TextView(this).apply {
        text = value
        setTextSize(TypedValue.COMPLEX_UNIT_SP, sizeSp)
        setTextColor(color)
    }

    private fun focusBackground() = StateListDrawable().apply {
        addState(intArrayOf(android.R.attr.state_focused), GradientDrawable().apply {
            setColor(FOCUSED)
            cornerRadius = dp(8).toFloat()
        })
        addState(intArrayOf(), GradientDrawable().apply { setColor(Color.TRANSPARENT) })
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
