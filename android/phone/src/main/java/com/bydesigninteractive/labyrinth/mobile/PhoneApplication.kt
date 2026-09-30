// Tells the shared updater which product this is before anything can use it.
package com.bydesigninteractive.labyrinth.mobile

import android.app.Application
import com.bydesigninteractive.labyrinth.update.MOBILE_PRODUCT
import com.bydesigninteractive.labyrinth.update.UpdateConfig

class PhoneApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        UpdateConfig.init(MOBILE_PRODUCT, BuildConfig.UPDATE_URL, BuildConfig.DEBUG, MobileGameActivity::class.java)
    }
}
