// Plays the remote test's click through SoundPool, which starts short sounds with little delay.
package com.bydesigninteractive.labyrinth.play

import android.content.Context
import android.media.AudioAttributes
import android.media.SoundPool
import com.bydesigninteractive.labyrinth.game.clickWav
import java.io.File
import java.io.IOException

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

    init {
        try {
            val file = File(context.cacheDir, "click.wav")
            file.writeBytes(clickWav())
            pool.setOnLoadCompleteListener { _, _, status ->
                ready = status == 0
                onReady()
            }
            id = pool.load(file.path, 1)
        } catch (_: IOException) {
            onReady() // the test still runs, without sound
        }
    }

    fun play() {
        if (ready) pool.play(id, 1f, 1f, 1, 0, 1f)
    }

    fun release() = pool.release()
}
