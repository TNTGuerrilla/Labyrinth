// The remote test's click: 20 ms of a 2 kHz tone with a fast decay, as a 16-bit mono WAV.
package com.bydesigninteractive.labyrinth.game

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.PI
import kotlin.math.exp
import kotlin.math.sin

const val CLICK_RATE = 44100

fun clickWav(): ByteArray {
    val samples = CLICK_RATE * 20 / 1000
    val data = ByteBuffer.allocate(samples * 2).order(ByteOrder.LITTLE_ENDIAN)
    for (i in 0 until samples) {
        val t = i.toDouble() / CLICK_RATE
        data.putShort((sin(2 * PI * 2000 * t) * exp(-t / 0.004) * 0.8 * Short.MAX_VALUE).toInt().toShort())
    }
    val header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).apply {
        put("RIFF".toByteArray())
        putInt(36 + samples * 2)
        put("WAVE".toByteArray())
        put("fmt ".toByteArray())
        putInt(16) // fmt chunk size
        putShort(1) // PCM
        putShort(1) // mono
        putInt(CLICK_RATE)
        putInt(CLICK_RATE * 2) // bytes per second
        putShort(2) // bytes per frame
        putShort(16) // bits per sample
        put("data".toByteArray())
        putInt(samples * 2)
    }
    return header.array() + data.array()
}
