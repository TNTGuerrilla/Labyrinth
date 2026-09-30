// The phone's update flow, with the same rules as the TV's settings screen: what is on offer,
// the download with its progress, the hand-off to Android's installer, Dismiss, Check now and
// the weekly-check switch. The game screen shows [status] in Menu > About, a dot on the Menu
// button while an update is on offer, and the update card on a fresh launch; [onChange] runs
// on the main thread whenever any of that changes.
package com.bydesigninteractive.labyrinth.mobile

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import com.bydesigninteractive.labyrinth.update.Release
import com.bydesigninteractive.labyrinth.update.UpdateFailure
import com.bydesigninteractive.labyrinth.update.UpdateStore
import com.bydesigninteractive.labyrinth.update.Updates
import com.bydesigninteractive.labyrinth.update.compareVersions
import com.bydesigninteractive.labyrinth.update.parseVersion
import com.bydesigninteractive.labyrinth.update.visibleUpdate
import java.io.IOException
import kotlin.concurrent.thread

class UpdateFlow(private val activity: Activity, private val onChange: () -> Unit) {
    var offered: Release? = null
        private set
    /** What Check now found this session, kept on offer even with weekly checks off. */
    private var sessionOffer: Release? = null
    private var downloading = false
    private var installing = false
    private var checkingNow = false
    private var justFailed = false
    private var message: String? = null

    val current: String get() = Updates.currentVersion(activity)
    val checksOn: Boolean get() = UpdateStore.enabled(activity)
    private val elsewhere: Boolean get() = Updates.isUpdating && !downloading

    /** Update and Dismiss can be offered right now. */
    val canUpdate: Boolean get() = offered != null && !downloading && !installing && !elsewhere

    val status: String
        get() = message
            ?: offered?.let { if (elsewhere) "Labyrinth ${it.version} is downloading." else "Labyrinth ${it.version} is available." }
            ?: "Version $current"

    private fun show(release: Release?, text: String? = null) {
        offered = release
        message = text
        onChange()
    }

    /** What earlier checks found, without the network: the launch card's offer. */
    fun pending(): Release? = Updates.pendingNotice(activity)

    /** The game came to the front: a weekly check when one is due, else the stored offer. */
    fun onResume() {
        // An installer that asked for confirmation while this app was in the background was
        // blocked by Android and reports nothing, so coming back offers Update again.
        installing = false
        if (justFailed) {
            justFailed = false // the failure message is showing; do not overwrite it right away
            return
        }
        if (!downloading) Updates.check(activity, force = false) { release -> onCheck(release) }
    }

    private fun onCheck(release: Release?) {
        if (activity.isDestroyed || downloading || checkingNow) return
        // A check that finds nothing must not drop an offer the player just chose on the card
        // (the Install unknown apps round trip resumes the game): keep it while it is still newer
        // than this install. Dismiss clears [offered], so a dismissed offer never survives here.
        show(release ?: sessionOffer ?: offered?.takeIf { newerThanCurrent(it) })
    }

    private fun newerThanCurrent(release: Release): Boolean {
        val offer = parseVersion(release.version) ?: return false
        val installed = parseVersion(current) ?: return true
        return compareVersions(offer, installed) > 0
    }

    /** InstallStatusActivity reported that the installer did not install the update. */
    fun installFailed() {
        installing = false
        val release = offered ?: visibleUpdate(UpdateStore.load(activity), current)
        show(release, "The update was not installed.")
        justFailed = true
    }

    /**
     * Downloads and installs [release]. The launch card passes the version it shows, which
     * becomes the offer: the resume check may not have set [offered] yet.
     */
    fun startUpdate(release: Release? = offered) {
        if (release == null) return
        offered = release
        if (!activity.packageManager.canRequestPackageInstalls()) {
            askForInstallPermission(release)
            return
        }
        if (!Updates.beginUpdate()) {
            show(release)
            return
        }
        downloading = true
        show(release, "Downloading Labyrinth ${release.version}...")
        thread(name = "update-download", isDaemon = true) {
            var nowInstalling = false
            val text = try {
                val downloaded = try {
                    Result.success(Updates.download(activity, release) { percent ->
                        activity.runOnUiThread {
                            if (!activity.isDestroyed) {
                                message = "Downloading Labyrinth ${release.version}: $percent%"
                                onChange()
                            }
                        }
                    })
                } catch (e: IOException) {
                    Result.failure(e)
                }
                downloaded.fold(
                    onSuccess = { apk ->
                        try {
                            Updates.install(activity, apk)
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
            activity.runOnUiThread {
                if (activity.isDestroyed) return@runOnUiThread
                downloading = false
                installing = nowInstalling
                show(release, text)
            }
        }
    }

    /** Android asks once per app before it lets an app install updates. */
    private fun askForInstallPermission(release: Release) {
        val intent = Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${activity.packageName}"))
        try {
            activity.startActivity(intent)
            show(release, "Allow Labyrinth to install apps, then come back and tap Update again.")
        } catch (_: ActivityNotFoundException) {
            show(release, "Allow installs from Labyrinth under Settings, Apps, Special app access, " +
                "Install unknown apps, then tap Update again.")
        }
    }

    /** Dismisses [release]; the launch card passes the version it shows, as for [startUpdate]. */
    fun dismiss(release: Release? = offered) {
        if (release == null) return
        offered = release
        UpdateStore.edit(activity) { it.copy(dismissed = release.version) }
        if (sessionOffer?.version == release.version) sessionOffer = null
        show(null)
    }

    fun toggleChecks() {
        val on = !checksOn
        UpdateStore.setEnabled(activity, on)
        show(sessionOffer)
        if (on) Updates.check(activity, force = true) { release -> onCheck(release) }
    }

    /** Check now: asks GitHub even with checks off, once at a time. */
    fun checkNow() {
        if (downloading || installing || checkingNow) return
        checkingNow = true
        message = "Checking..."
        onChange()
        Updates.checkNow(activity) { outcome ->
            checkingNow = false
            if (activity.isDestroyed || downloading) return@checkNow
            when (outcome) {
                is Updates.CheckOutcome.Available -> {
                    sessionOffer = outcome.release
                    show(outcome.release)
                }
                Updates.CheckOutcome.UpToDate -> {
                    sessionOffer = null
                    show(null, "Up to date")
                }
                is Updates.CheckOutcome.Failed -> show(offered, outcome.message)
            }
        }
    }
}
