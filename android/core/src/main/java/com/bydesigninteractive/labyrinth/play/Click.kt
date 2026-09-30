// Plays the remote test's click through SoundPool, which starts short sounds with little delay.
package com.bydesigninteractive.labyrinth.play

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool
import android.os.Handler
import android.os.Looper
import com.bydesigninteractive.labyrinth.game.clickWav
import java.io.File
import java.io.IOException

/** How long the click may take to load before the test goes on without it. */
private const val LOAD_TIMEOUT_MS = 3000L

class Click(context: Context, onReady: () -> Unit) {
    private val pool: SoundPool = SoundPool.Builder()
        .setMaxStreams(4)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_GAME)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build(),
        )
        .build()
    private var id = 0
    private var ready = false
    private val handler = Handler(Looper.getMainLooper())
    // Cleared once called, so a load that reports after the timeout changes nothing.
    private var onReady: (() -> Unit)? = onReady

    init {
        try {
            val file = File(context.cacheDir, "click.wav")
            file.writeBytes(clickWav())
            pool.setOnLoadCompleteListener { _, _, status ->
                if (this.onReady == null) return@setOnLoadCompleteListener
                ready = status == 0
                done()
            }
            id = pool.load(file.path, 1)
            // 0 means the load failed; otherwise the callback may still never come.
            if (id == 0) done() else handler.postDelayed(::done, LOAD_TIMEOUT_MS)
        } catch (_: IOException) {
            done() // the test still runs, without sound
        }
    }

    /** Calls onReady once: when the click loaded, failed to load, or took too long. */
    private fun done() {
        val callback = onReady ?: return
        onReady = null
        handler.removeCallbacksAndMessages(null)
        callback()
    }

    fun play() {
        if (ready) pool.play(id, 1f, 1f, 1, 0, 1f)
    }

    fun release() {
        onReady = null
        handler.removeCallbacksAndMessages(null)
        pool.release()
    }
}
