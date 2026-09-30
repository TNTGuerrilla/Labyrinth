// What the shared updater needs from the app it runs in. Each app's Application sets it in
// onCreate, before any activity, service or dream can use the updater.
package com.bydesigninteractive.labyrinth.update

import android.app.Activity

object UpdateConfig {
    lateinit var product: Product
        private set
    /** GitHub's release list, or the local fake release server in debug builds. */
    lateinit var releasesUrl: String
        private set
    /** Debug builds may also download over plain http from the fake release server. */
    var debug = false
        private set
    /** The screen InstallStatusActivity brings back with [Updates.EXTRA_INSTALL_FAILED]. */
    lateinit var failureScreen: Class<out Activity>
        private set

    fun init(product: Product, releasesUrl: String, debug: Boolean, failureScreen: Class<out Activity>) {
        this.product = product
        this.releasesUrl = releasesUrl
        this.debug = debug
        this.failureScreen = failureScreen
    }
}
