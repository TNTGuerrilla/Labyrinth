// The app's launcher screen: screensaver settings, built for a TV remote. Up and down move
// between rows, left and right change the focused value (hold to speed up), and changes
// save as they are made. Also opened from the system screensaver settings, when a TV shows them.
package com.bydesigninteractive.labyrinth

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
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
import com.bydesigninteractive.labyrinth.maze.Field
import com.bydesigninteractive.labyrinth.maze.Settings
import com.bydesigninteractive.labyrinth.update.Release
import com.bydesigninteractive.labyrinth.update.UpdateFailure
import com.bydesigninteractive.labyrinth.update.UpdateStore
import com.bydesigninteractive.labyrinth.update.Updates
import java.io.IOException
import java.net.Inet4Address
import kotlin.concurrent.thread

private val BACKGROUND = Color.rgb(16, 18, 22)
private val FOCUSED = Color.rgb(52, 58, 70)
private val TEXT = Color.rgb(230, 230, 230)
private val DIM_TEXT = Color.rgb(150, 150, 150)
private val ACCENT = Color.rgb(60, 220, 90)
// Between BACKGROUND and FOCUSED, so the command box shows whether or not the help has focus.
private val CODE_BACKGROUND = Color.rgb(30, 34, 42)

private const val GUIDE_URL = "github.com/TNTGuerrilla/Labyrinth"

class SettingsActivity : Activity() {
    private lateinit var settings: Settings
    private val valueViews = HashMap<Field, TextView>()
    private lateinit var help: LinearLayout
    private lateinit var updateStatus: TextView
    private lateinit var updateButton: TextView
    private lateinit var dismissButton: TextView
    private lateinit var checkToggle: TextView
    private var offered: Release? = null
    private var downloading = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        settings = SettingsStore.load(this)

        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(64), dp(40), dp(64), dp(40))
        }
        column.addView(text("Labyrinth", 30f, TEXT).apply {
            typeface = Typeface.DEFAULT_BOLD
            setPadding(dp(16), 0, dp(16), dp(16))
        })
        var first: View? = null
        for (field in Field.entries) {
            val row = fieldRow(field)
            column.addView(row)
            if (first == null) first = row
        }
        column.addView(button("Preview screensaver") { startActivity(Intent(this, PreviewActivity::class.java)) })
        column.addView(button("Reset to defaults") { update(Settings()) })
        updateStatus = text("", 17f, DIM_TEXT).apply { setPadding(dp(16), dp(16), dp(16), dp(4)) }
        column.addView(updateStatus)
        updateButton = button("Update") { startUpdate() }
        column.addView(updateButton)
        dismissButton = button("Dismiss") { dismissUpdate() }
        column.addView(dismissButton)
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

        setContentView(ScrollView(this).apply {
            setBackgroundColor(BACKGROUND)
            addView(column)
        })
        refresh()
        first?.requestFocus()
    }

    override fun onResume() {
        super.onResume()
        // Refreshed here so the status is current after running the ADB command.
        showSetupHelp()
        if (!downloading) Updates.check(this, force = true) { if (!isDestroyed && !downloading) showUpdate(it) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        if (intent.action != Updates.ACTION_INSTALL_STATUS) return
        when (intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirm = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION") intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                }
                confirm?.let { startActivity(it) }
            }
            PackageInstaller.STATUS_SUCCESS -> {} // Android replaces this app now.
            else -> showUpdate(offered, "The update was not installed.")
        }
    }

    /** The update row: what is on offer, or the running version, and the check switch. */
    private fun showUpdate(release: Release?, message: String? = null) {
        offered = release
        val enabled = UpdateStore.enabled(this)
        checkToggle.text = "Check for updates: ${if (enabled) "On" else "Off"}"
        updateStatus.text = message
            ?: release?.let { "Labyrinth ${it.version} is available." }
            ?: "Version ${Updates.currentVersion(this)}"
        val actions = if (release != null && !downloading) View.VISIBLE else View.GONE
        updateButton.visibility = actions
        dismissButton.visibility = actions
    }

    private fun startUpdate() {
        val release = offered ?: return
        if (!packageManager.canRequestPackageInstalls()) {
            askForInstallPermission(release)
            return
        }
        downloading = true
        showUpdate(release, "Downloading Labyrinth ${release.version}...")
        checkToggle.requestFocus()
        thread(name = "update-download", isDaemon = true) {
            val downloaded = try {
                Result.success(Updates.download(this, release) { percent ->
                    runOnUiThread { if (!isDestroyed) updateStatus.text = "Downloading Labyrinth ${release.version}: $percent%" }
                })
            } catch (e: IOException) {
                Result.failure(e)
            }
            val message = downloaded.fold(
                onSuccess = { apk ->
                    try {
                        Updates.install(this, apk)
                        "Installing Labyrinth ${release.version}..."
                    } catch (_: IOException) {
                        "The update could not be installed."
                    }
                },
                onFailure = { (it as? UpdateFailure)?.message ?: "The download was interrupted." },
            )
            runOnUiThread {
                if (isDestroyed) return@runOnUiThread
                downloading = false
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
        UpdateStore.save(this, UpdateStore.load(this).copy(dismissed = release.version))
        showUpdate(null)
        checkToggle.requestFocus()
    }

    private fun toggleChecks() {
        val enabled = !UpdateStore.enabled(this)
        UpdateStore.setEnabled(this, enabled)
        showUpdate(null)
        if (enabled) Updates.check(this, force = true) { if (!isDestroyed && !downloading) showUpdate(it) }
    }

    private fun fieldRow(field: Field): LinearLayout {
        val value = text("", 20f, ACCENT).apply {
            gravity = Gravity.END
            typeface = Typeface.MONOSPACE
        }
        valueViews[field] = value
        return LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(16), dp(10), dp(16), dp(10))
            isFocusable = true
            background = focusBackground()
            addView(text(field.label, 20f, TEXT), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
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
    }

    private fun button(label: String, onClick: () -> Unit): TextView =
        text(label, 20f, TEXT).apply {
            setPadding(dp(16), dp(12), dp(16), dp(12))
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
        code(
            "\$adb = \"\$env:LOCALAPPDATA\\Android\\Sdk\\platform-tools\\adb.exe\"",
            "& \$adb connect ${ip ?: "<TV IP address>"}:5555",
            "& \$adb shell settings put secure screensaver_components $component",
        )
        paragraph(
            buildString {
                if (ip == null) append("Find this TV's IP address under Settings, Network & Internet. ")
                append("After the connect command, choose Always allow on the \"Allow USB debugging?\" prompt on this TV.")
            },
            DIM_TEXT,
        )
        paragraph("On TCL TVs, also allow Auto Launch for this app so it can start when the TV is idle.", DIM_TEXT)
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
