// The maze surface shared by the screensaver and the preview screen.
//
// The maze image lives in a GPU texture. Each frame, on GLSurfaceView's render thread, the
// Board steps, BoardRenderer draws only the changed cells into a CPU bitmap, and just that
// changed rectangle is uploaded into the texture before the GPU draws it to the screen.
// This avoids Surface.lockCanvas, whose software path copies the whole previous frame on
// every call (several milliseconds per frame, even for a few changed cells).
package io.github.tntguerrilla.mazesaver

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Rect
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Process
import io.github.tntguerrilla.mazesaver.maze.Board
import io.github.tntguerrilla.mazesaver.maze.FIRST_DELAY_MAX
import io.github.tntguerrilla.mazesaver.maze.Settings
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.IntBuffer
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.random.Random

/** Longest step the board takes after a stall, so a paused thread does not jump ahead. */
private const val MAX_FRAME_SECONDS = 0.25

/** Rows per texture upload, which bounds the scratch pixel array. */
private const val UPLOAD_ROWS = 64

class MazeView(context: Context, settings: Settings) : GLSurfaceView(context) {
    init {
        setEGLContextClientVersion(2)
        setEGLConfigChooser(8, 8, 8, 0, 0, 0)
        preserveEGLContextOnPause = true
        setRenderer(MazeRenderer(settings))
        renderMode = RENDERMODE_CONTINUOUSLY
    }
}

private val VERTEX_SHADER = """
    attribute vec2 aPos;
    varying highp vec2 vUv;
    void main() {
        vUv = vec2((aPos.x + 1.0) * 0.5, (1.0 - aPos.y) * 0.5);
        gl_Position = vec4(aPos, 0.0, 1.0);
    }
""".trimIndent()

// Bitmap.getPixels gives ARGB ints, which land in memory as B, G, R, A bytes; the texture
// is uploaded as RGBA, so the shader swaps red and blue back.
private val FRAGMENT_SHADER = """
    precision mediump float;
    uniform sampler2D uTex;
    varying highp vec2 vUv;
    void main() {
        gl_FragColor = vec4(texture2D(uTex, vUv).bgr, 1.0);
    }
""".trimIndent()

private class MazeRenderer(private val settings: Settings) : GLSurfaceView.Renderer {
    private val rng = Random.Default
    private val renderer = BoardRenderer()
    private var board: Board? = null
    private var buffer: Bitmap? = null
    private var bufferCanvas: Canvas? = null
    private var width = 0
    private var height = 0

    private var program = 0
    private var texture = 0
    private var textureWidth = 0
    private var textureHeight = 0
    private var needsFullUpload = true
    private var pixels = IntArray(0)
    private var lastFrameNanos = 0L

    private val quad: FloatBuffer = ByteBuffer.allocateDirect(8 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        .apply { put(floatArrayOf(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f)).position(0) }

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        // Display priority, the same class Android gives its own UI thread, so background
        // work on a busy TV does not preempt frames.
        Process.setThreadPriority(Process.THREAD_PRIORITY_DISPLAY)
        // A new context means any earlier program and texture are gone.
        program = buildProgram()
        val ids = IntArray(1)
        GLES20.glGenTextures(1, ids, 0)
        texture = ids[0]
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
        for ((name, value) in listOf(
            GLES20.GL_TEXTURE_MIN_FILTER to GLES20.GL_NEAREST,
            GLES20.GL_TEXTURE_MAG_FILTER to GLES20.GL_NEAREST,
            GLES20.GL_TEXTURE_WRAP_S to GLES20.GL_CLAMP_TO_EDGE,
            GLES20.GL_TEXTURE_WRAP_T to GLES20.GL_CLAMP_TO_EDGE,
        )) GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, name, value)
        textureWidth = 0
        textureHeight = 0
        lastFrameNanos = 0L
    }

    override fun onSurfaceChanged(gl: GL10?, w: Int, h: Int) {
        GLES20.glViewport(0, 0, w, h)
        if (board == null || w != width || h != height) {
            width = w
            height = h
            buffer?.recycle()
            buffer = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888).also { bufferCanvas = Canvas(it) }
            board = Board(w, h, settings, rng, rng.nextDouble(0.0, FIRST_DELAY_MAX))
        }
        if (textureWidth != w || textureHeight != h) {
            GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
            GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, w, h, 0, GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
            textureWidth = w
            textureHeight = h
        }
        needsFullUpload = true
    }

    override fun onDrawFrame(gl: GL10?) {
        val b = board ?: return
        val now = System.nanoTime()
        val dt = if (lastFrameNanos == 0L) 0.0 else ((now - lastFrameNanos) / 1e9).coerceIn(0.0, MAX_FRAME_SECONDS)
        lastFrameNanos = now
        val drawn = renderer.apply(bufferCanvas!!, b, b.update(dt))
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
        if (needsFullUpload) {
            upload(Rect(0, 0, width, height))
            needsFullUpload = false
        } else if (drawn != null) {
            upload(drawn)
        }
        drawQuad()
    }

    /** Copies one rectangle of the bitmap into the texture, a band of rows at a time. */
    private fun upload(area: Rect) {
        val bmp = buffer ?: return
        if (!area.intersect(0, 0, width, height)) return
        val w = area.width()
        if (pixels.size < w * UPLOAD_ROWS) pixels = IntArray(w * UPLOAD_ROWS)
        var top = area.top
        while (top < area.bottom) {
            val rows = minOf(UPLOAD_ROWS, area.bottom - top)
            bmp.getPixels(pixels, 0, w, area.left, top, w, rows)
            GLES20.glTexSubImage2D(GLES20.GL_TEXTURE_2D, 0, area.left, top, w, rows, GLES20.GL_RGBA,
                GLES20.GL_UNSIGNED_BYTE, IntBuffer.wrap(pixels, 0, w * rows))
            top += rows
        }
    }

    private fun drawQuad() {
        GLES20.glUseProgram(program)
        val pos = GLES20.glGetAttribLocation(program, "aPos")
        GLES20.glEnableVertexAttribArray(pos)
        GLES20.glVertexAttribPointer(pos, 2, GLES20.GL_FLOAT, false, 0, quad)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    }

    private fun buildProgram(): Int {
        val p = GLES20.glCreateProgram()
        GLES20.glAttachShader(p, compile(GLES20.GL_VERTEX_SHADER, VERTEX_SHADER))
        GLES20.glAttachShader(p, compile(GLES20.GL_FRAGMENT_SHADER, FRAGMENT_SHADER))
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
}
