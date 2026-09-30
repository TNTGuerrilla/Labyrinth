// OpenGL helpers shared by the screensaver's MazeView and the game's GameView.
package com.bydesigninteractive.labyrinth

import android.graphics.Bitmap
import android.graphics.Rect
import android.opengl.GLES20
import java.nio.Buffer
import java.nio.IntBuffer

/** Rows per texture upload, which bounds the scratch pixel array. */
private const val UPLOAD_ROWS = 64

fun buildProgram(vertex: String, fragment: String): Int {
    val p = GLES20.glCreateProgram()
    GLES20.glAttachShader(p, compile(GLES20.GL_VERTEX_SHADER, vertex))
    GLES20.glAttachShader(p, compile(GLES20.GL_FRAGMENT_SHADER, fragment))
    GLES20.glLinkProgram(p)
    val ok = IntArray(1)
    GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, ok, 0)
    check(ok[0] != 0) { "shader link failed: ${GLES20.glGetProgramInfoLog(p)}" }
    return p
}

private fun compile(type: Int, source: String): Int {
    val s = GLES20.glCreateShader(type)
    GLES20.glShaderSource(s, source)
    GLES20.glCompileShader(s)
    val ok = IntArray(1)
    GLES20.glGetShaderiv(s, GLES20.GL_COMPILE_STATUS, ok, 0)
    check(ok[0] != 0) { "shader compile failed: ${GLES20.glGetShaderInfoLog(s)}" }
    return s
}

/**
 * Copies rectangles of a bitmap into the bound texture, a band of rows at a time.
 * Bitmap.getPixels gives ARGB ints, which land in memory as B, G, R, A bytes; the texture
 * is uploaded as RGBA, so shaders swap red and blue back.
 */
class TextureUploader {
    private var pixels = IntArray(0)
    private var pixelBuffer: IntBuffer = IntBuffer.wrap(pixels)

    fun upload(bmp: Bitmap, area: Rect) {
        if (!area.intersect(0, 0, bmp.width, bmp.height)) return
        val w = area.width()
        if (pixels.size < w * UPLOAD_ROWS) {
            pixels = IntArray(w * UPLOAD_ROWS)
            pixelBuffer = IntBuffer.wrap(pixels)
        }
        var top = area.top
        while (top < area.bottom) {
            val rows = minOf(UPLOAD_ROWS, area.bottom - top)
            bmp.getPixels(pixels, 0, w, area.left, top, w, rows)
            GLES20.glTexSubImage2D(GLES20.GL_TEXTURE_2D, 0, area.left, top, w, rows, GLES20.GL_RGBA,
                GLES20.GL_UNSIGNED_BYTE, (pixelBuffer as Buffer).clear().limit(w * rows))
            top += rows
        }
    }
}
