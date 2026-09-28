// Talks to GitHub and to Android's installer. Network work runs on background threads;
// results come back on the main thread.
package com.bydesigninteractive.labyrinth.update

import android.app.Activity
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.os.Build
import android.os.Handler
import android.os.Looper
import com.bydesigninteractive.labyrinth.BuildConfig
import com.bydesigninteractive.labyrinth.SettingsActivity
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.concurrent.thread

/** A failed download or install. The message is a sentence for the user. */
class UpdateFailure(message: String) : IOException(message)

object Updates {
    const val ACTION_INSTALL_STATUS = "com.bydesigninteractive.labyrinth.INSTALL_STATUS"
    private const val TIMEOUT_MS = 15_000
    private val checking = AtomicBoolean(false)

    fun currentVersion(context: Context): String =
        context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: ""

    /**
     * Calls [onDone] on the main thread with the update to offer, if any. Asks GitHub first
     * when checks are on and a week has passed, or when [force] is set (the settings screen
     * opened). With checks off it answers null without any network access.
     */
    fun check(context: Context, force: Boolean, onDone: (Release?) -> Unit) {
        val app = context.applicationContext
        if (!UpdateStore.enabled(app)) {
            onDone(null)
            return
        }
        val current = currentVersion(app)
        val state = UpdateStore.load(app)
        if ((!force && !isDue(state, System.currentTimeMillis())) || !checking.compareAndSet(false, true)) {
            onDone(visibleUpdate(state, current))
            return
        }
        val main = Handler(Looper.getMainLooper())
        thread(name = "update-check", isDaemon = true) {
            val offer = try {
                val found = newestRelease(fetch(BuildConfig.UPDATE_URL), current)
                val next = UpdateStore.load(app).copy(lastCheck = System.currentTimeMillis(), found = found)
                UpdateStore.save(app, next)
                visibleUpdate(next, current)
            } catch (_: IOException) {
                visibleUpdate(UpdateStore.load(app), current)
            } finally {
                checking.set(false)
            }
            main.post { onDone(offer) }
        }
    }

    private fun open(url: String, accept: String): HttpURLConnection =
        (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = TIMEOUT_MS
            readTimeout = TIMEOUT_MS
            setRequestProperty("User-Agent", "Labyrinth-TV-updater")
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

    private fun fetch(url: String): String {
        val connection = open(url, "application/vnd.github+json")
        try {
            if (connection.responseCode != 200) throw IOException("HTTP ${connection.responseCode}")
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    /** Downloads the APK into app storage and checks its SHA-256. Runs on the caller's thread. */
    fun download(context: Context, release: Release, onProgress: (Int) -> Unit): File {
        val file = File(context.cacheDir, "update.apk")
        val digest = MessageDigest.getInstance("SHA-256")
        val connection = connect(release.url, "application/octet-stream")
        try {
            if (connection.responseCode != 200) throw UpdateFailure("Could not reach the update server.")
            val total = connection.contentLengthLong
            var done = 0L
            var lastPercent = -1
            connection.inputStream.use { input ->
                file.outputStream().use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        output.write(buffer, 0, n)
                        digest.update(buffer, 0, n)
                        done += n
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
     * Hands the APK to Android's installer. Android reports back to SettingsActivity with
     * [ACTION_INSTALL_STATUS], first asking for the user's confirmation. Copies the whole
     * APK and fsyncs it, so this must not be called on the main thread.
     */
    fun install(activity: Activity, apk: File) {
        val installer = activity.packageManager.packageInstaller
        val params = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL)
        params.setAppPackageName(activity.packageName)
        val id = installer.createSession(params)
        installer.openSession(id).use { session ->
            try {
                session.openWrite(ASSET_NAME, 0, apk.length()).use { out ->
                    apk.inputStream().use { it.copyTo(out) }
                    session.fsync(out)
                }
                val intent = Intent(activity, SettingsActivity::class.java).setAction(ACTION_INSTALL_STATUS)
                val flags = PendingIntent.FLAG_UPDATE_CURRENT or
                    (if (Build.VERSION.SDK_INT >= 31) PendingIntent.FLAG_MUTABLE else 0)
                session.commit(PendingIntent.getActivity(activity, 0, intent, flags).intentSender)
            } catch (e: Exception) {
                session.abandon()
                throw e
            }
        }
    }
}
