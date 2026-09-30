// Tells the shared updater which product this is before anything can use it.
package com.bydesigninteractive.labyrinth

import android.app.Application
import com.bydesigninteractive.labyrinth.update.TV_PRODUCT
import com.bydesigninteractive.labyrinth.update.UpdateConfig

class TvApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        UpdateConfig.init(TV_PRODUCT, BuildConfig.UPDATE_URL, BuildConfig.DEBUG, SettingsActivity::class.java)
    }
}
