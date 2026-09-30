// Talks to GitHub and to Android's installer. Network work runs on background threads;
// results come back on the main thread.
package com.bydesigninteractive.labyrinth.update

import android.app.Activity
import android.app.ActivityOptions
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread
import org.json.JSONArray
import org.json.JSONException

/** A failed download or install. The message is a sentence for the user. */
class UpdateFailure(message: String) : IOException(message)

object Updates {
    /** Set on the intent that brings the app's update screen back after an install did not happen. */
    const val EXTRA_INSTALL_FAILED = "com.bydesigninteractive.labyrinth.INSTALL_FAILED"
    private const val TIMEOUT_MS = 15_000
    /** Far above any real APK, so a wrong or hostile file cannot fill the device's storage. */
    private const val MAX_DOWNLOAD_BYTES = 300L * 1024 * 1024
    private val checking = AtomicBoolean(false)
    private val updating = AtomicBoolean(false)
    // Set when install() commits a session and cleared when its report reaches this app, so the
    // exported settings screen ignores an install failure extra this process did not cause.
    private val awaitingInstall = AtomicBoolean(false)
    /** When a check last reached GitHub and read the list, on the monotonic clock. */
    @Volatile private var lastSuccessAt: Long? = null

    /**
     * Claims the one update download for the whole process. A download keeps running after
     * the activity that started it is gone, and every download writes the same file, so a
     * second one must not start until [endUpdate] is called.
     */
    fun beginUpdate(): Boolean = updating.compareAndSet(false, true)

    fun endUpdate() = updating.set(false)

    val isUpdating: Boolean get() = updating.get()

    /**
     * Whether an install this process committed is still waiting for its report, clearing it.
     * InstallStatusActivity's failure report is honored only when this is true.
     */
    fun takeInstallReport(): Boolean = awaitingInstall.getAndSet(false)

    fun currentVersion(context: Context): String =
        context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: ""

    /** The update to offer from what earlier checks found, without any network access. */
    fun pendingNotice(context: Context): Release? {
        val app = context.applicationContext
        return pendingNotice(UpdateStore.enabled(app), UpdateStore.load(app), currentVersion(app))
    }

    /**
     * Calls [onDone] on the main thread with the update to offer, if any. Asks GitHub first
     * when checks are on and a week has passed, or when [force] is set (the settings screen
     * opened) and no check succeeded in the last ten minutes. With checks off it answers null
     * without any network access.
     */
    fun check(context: Context, force: Boolean, onDone: (Release?) -> Unit) {
        val app = context.applicationContext
        if (!UpdateStore.enabled(app)) {
            onDone(null)
            return
        }
        val current = currentVersion(app)
        val state = UpdateStore.load(app)
        val ask = if (force) {
            !checkedRecently(lastSuccessAt, SystemClock.elapsedRealtime())
        } else {
            isDue(state, System.currentTimeMillis())
        }
        if (!ask || !checking.compareAndSet(false, true)) {
            onDone(visibleUpdate(state, current))
            return
        }
        val main = Handler(Looper.getMainLooper())
        thread(name = "update-check", isDaemon = true) {
            val offer = try {
                val json = fetch(UpdateConfig.releasesUrl)
                requireListing(json)
                val found = newestRelease(json, current, UpdateConfig.product)
                if (found != null) {
                    val fresh = collectNotes(json, current, found.version, UpdateConfig.product)
                    UpdateStore.editSeen(app) { it.copy(notes = mergeNotes(it.notes, fresh, current)) }
                }
                val next = UpdateStore.edit(app) { it.copy(lastCheck = System.currentTimeMillis(), found = found) }
                lastSuccessAt = SystemClock.elapsedRealtime()
                visibleUpdate(next, current)
            } catch (_: Exception) {
                // Offline, a server error or a list that could not be read: a failed check.
                visibleUpdate(UpdateStore.load(app), current)
            } finally {
                checking.set(false)
            }
            main.post { onDone(offer) }
        }
    }

    private fun open(url: String, accept: String): HttpURLConnection =
        (URL(url).openConnection() as? HttpURLConnection ?: throw UpdateFailure("The update's address is not allowed.")).apply {
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            setRequestProperty("User-Agent", UpdateConfig.product.userAgent)
            setRequestProperty("Accept", accept)
        }

    /** Wraps opening the connection and reading its response code: unreachable, not interrupted. */
    private fun connect(url: String, accept: String): HttpURLConnection {
        var connection: HttpURLConnection? = null
        try {
            connection = open(url, accept)
            connection.responseCode
            return connection
        } catch (_: IOException) {
            connection?.disconnect()
            throw UpdateFailure("Could not reach the update server.")
        }
    }

    /** Parses `json` as the release list GitHub returns, or throws when it cannot be read. */
    private fun requireListing(json: String): JSONArray =
        try {
            JSONArray(json)
        } catch (_: JSONException) {
            throw UpdateFailure("Could not read the list of releases.")
        }

    private fun fetch(url: String): String {
        val connection = open(url, "application/vnd.github+json")
        try {
            if (connection.responseCode != 200) throw IOException("HTTP ${connection.responseCode}")
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    /**
     * Downloads the APK into app storage and checks its SHA-256. Runs on the caller's thread.
     * Only GitHub addresses are used (see [isAllowedDownloadUrl]), before and after redirects.
     */
    fun download(context: Context, release: Release, onProgress: (Int) -> Unit): File {
        val file = File(context.cacheDir, "update.apk")
        val digest = MessageDigest.getInstance("SHA-256")
        val notAllowed = "The update's address is not allowed."
        if (!isAllowedDownloadUrl(release.url, UpdateConfig.debug)) throw UpdateFailure(notAllowed)
        val connection = connect(release.url, "application/octet-stream")
        try {
            // Redirects are followed within https (or within http), so check where they led.
            if (!isAllowedDownloadUrl(connection.url.toString(), UpdateConfig.debug)) throw UpdateFailure(notAllowed)
            if (connection.responseCode != 200) throw UpdateFailure("Could not reach the update server.")
            val total = connection.contentLengthLong
            val tooLarge = "The download was larger than an update can be."
            if (total > MAX_DOWNLOAD_BYTES) throw UpdateFailure(tooLarge)
            var done = 0L
            var lastPercent = -1
            connection.inputStream.use { input ->
                file.outputStream().use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        done += n
                        if (done > MAX_DOWNLOAD_BYTES) throw UpdateFailure(tooLarge)
                        output.write(buffer, 0, n)
                        digest.update(buffer, 0, n)
                        if (total > 0) {
                            val percent = (done * 100 / total).toInt()
                            if (percent != lastPercent) {
                                lastPercent = percent
                                onProgress(percent)
                            }
                        }
                    }
                }
            }
            if (total > 0 && done < total) {
                file.delete()
                throw UpdateFailure("The download was interrupted.")
            }
        } catch (e: UpdateFailure) {
            file.delete()
            throw e
        } catch (_: IOException) {
            file.delete()
            throw UpdateFailure("The download was interrupted.")
        } finally {
            connection.disconnect()
        }
        val hex = digest.digest().joinToString("") { "%02x".format(it) }
        if (hex != release.sha256) {
            file.delete()
            throw UpdateFailure("The download did not match its published checksum.")
        }
        return file
    }

    /**
     * Hands the APK to Android's installer. Android reports back to [InstallStatusActivity]
     * (not exported), first asking for the user's confirmation. Copies the whole APK and
     * fsyncs it, so this must not be called on the main thread.
     */
    fun install(activity: Activity, apk: File) {
        val installer = activity.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        params.setAppPackageName(activity.packageName)
        val id = installer.createSession(params)
        installer.openSession(id).use { session ->
            try {
                session.openWrite(UpdateConfig.product.assetName, 0, apk.length()).use { out ->
                    apk.inputStream().use { it.copyTo(out) }
                    session.fsync(out)
                }
                val intent = Intent(activity, InstallStatusActivity::class.java)
                val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                    (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
                // From Android 15 (targetSdk 35) the installer's report cannot start an activity
                // of this app unless the app, as the PendingIntent's creator, allows it. Without
                // this the report is blocked as a background activity launch and the confirmation
                // never shows. The option exists from Android 14; older versions allow it anyway.
                val options = if (Build.VERSION.SDK_INT >= 34) {
                    ActivityOptions.makeBasic().setPendingIntentCreatorBackgroundActivityStartMode(
                        ActivityOptions.MODE_BACKGROUND_ACTIVITY_START_ALLOWED,
                    ).toBundle()
                } else {
                    null
                }
                // Set first: the installer may report back before commit returns.
                awaitingInstall.set(true)
                session.commit(PendingIntent.getActivity(activity, 0, intent, flags, options).intentSender)
            } catch (e: Exception) {
                awaitingInstall.set(false)
                session.abandon()
                throw e
            }
        }
    }

    sealed class CheckOutcome {
        data class Available(val release: Release) : CheckOutcome()
        object UpToDate : CheckOutcome()
        data class Failed(val message: String) : CheckOutcome()
    }

    /**
     * The user selected Check now: asks GitHub even with checks off and reports the outcome on
     * the main thread. A dismissed version found this way is offered again.
     */
    fun checkNow(context: Context, onDone: (CheckOutcome) -> Unit) {
        val app = context.applicationContext
        val main = Handler(Looper.getMainLooper())
        if (!checking.compareAndSet(false, true)) {
            // An automatic check is in flight: ask again once it has had time to finish.
            main.postDelayed({ checkNow(app, onDone) }, 500)
            return
        }
        val current = currentVersion(app)
        thread(name = "update-check-now", isDaemon = true) {
            val outcome = try {
                val json = fetch(UpdateConfig.releasesUrl)
                requireListing(json)
                val found = newestRelease(json, current, UpdateConfig.product)
                if (found != null) {
                    val fresh = collectNotes(json, current, found.version, UpdateConfig.product)
                    UpdateStore.editSeen(app) { it.copy(notes = mergeNotes(it.notes, fresh, current)) }
                }
                val next = UpdateStore.edit(app) { state ->
                    val cleared = if (found != null && state.dismissed == found.version) null else state.dismissed
                    state.copy(lastCheck = System.currentTimeMillis(), found = found, dismissed = cleared)
                }
                lastSuccessAt = SystemClock.elapsedRealtime()
                visibleUpdate(next, current)?.let { CheckOutcome.Available(it) } ?: CheckOutcome.UpToDate
            } catch (e: UpdateFailure) {
                CheckOutcome.Failed(e.message ?: "Could not reach the update server.")
            } catch (_: Exception) {
                CheckOutcome.Failed("Could not reach the update server.")
            } finally {
                checking.set(false)
            }
            main.post { onDone(outcome) }
        }
    }
}
