// The screensaver itself. Android starts this when the TV goes idle; any remote button
// press ends it, since the dream is not interactive.
package com.bydesigninteractive.labyrinth

import android.service.dreams.DreamService

class LabyrinthDreamService : DreamService() {
    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        isInteractive = false
        isFullscreen = true
        isScreenBright = true
        setContentView(MazeView(this, SettingsStore.load(this)))
    }
}
