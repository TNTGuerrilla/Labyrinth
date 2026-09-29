// Receives Android's installer reports for an update. It is not exported, so only the
// installer (through the PendingIntent that Updates.install gives it) and this app can start
// it; the exported launcher screen never acts on an installer report.
package com.bydesigninteractive.labyrinth.update

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.content.pm.PackageInstaller
import android.os.Build
import android.os.Bundle
import com.bydesigninteractive.labyrinth.SettingsActivity

class InstallStatusActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handle(intent)
        finish()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handle(intent)
        finish()
    }

    private fun handle(intent: Intent?) {
        when (intent?.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
            PackageInstaller.STATUS_PENDING_USER_ACTION -> {
                val confirm = if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent::class.java)
                } else {
                    @Suppress("DEPRECATION") intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT)
                }
                try {
                    if (confirm != null) startActivity(confirm) else reportFailure()
                } catch (_: ActivityNotFoundException) {
                    reportFailure()
                }
            }
            PackageInstaller.STATUS_SUCCESS -> Updates.takeInstallReport() // Android replaces this app now.
            else -> reportFailure()
        }
    }

    /** Brings the settings screen back with "The update was not installed." and Update again. */
    private fun reportFailure() {
        startActivity(
            Intent(this, SettingsActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                .putExtra(Updates.EXTRA_INSTALL_FAILED, true),
        )
    }
}
