// The maze surface shared by the screensaver and the preview screen.
//
// The maze image lives in a GPU texture. Each frame, on GLSurfaceView's render thread, the
// Board steps, BoardRenderer draws only the changed cells into a CPU bitmap, and just those
// cells are uploaded into the texture before the GPU draws it to the screen. Cells are
// uploaded one by one rather than as their bounding box, because leads growing in opposite
// corners would make that box cover most of the maze every frame.
// This avoids Surface.lockCanvas, whose software path copies the whole previous frame on
// every call (several milliseconds per frame, even for a few changed cells).
package com.bydesigninteractive.labyrinth

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Rect
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Handler
import android.os.Looper
import android.os.Process
import com.bydesigninteractive.labyrinth.maze.Board
import com.bydesigninteractive.labyrinth.maze.FIRST_DELAY_MAX
import com.bydesigninteractive.labyrinth.maze.Settings
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.random.Random

/** Longest step the board takes after a stall, so a paused thread does not jump ahead. */
private const val MAX_FRAME_SECONDS = 0.25

/** Past this many changed cells in one frame, one bounding-box upload is cheaper. */
private const val MAX_CELL_UPLOADS = 64

/** Board events the dream acts on, delivered on the main thread (at most twice per maze). */
interface MazeListener {
    fun onMazeSolved()
    fun onMazeCleared()
}

/** [notice]: the update notice shows, so every maze keeps within NOTICE_COVERAGE. */
class MazeView(context: Context, settings: Settings, notice: Boolean = false) : GLSurfaceView(context) {
    private val mazeRenderer = MazeRenderer(settings, notice)

    var listener: MazeListener?
        get() = mazeRenderer.listener
        set(value) { mazeRenderer.listener = value }

    /** Keeps mazes within NOTICE_COVERAGE (or not) from the next maze on. */
    fun setNotice(on: Boolean) {
        queueEvent { mazeRenderer.setNotice(on) }
    }

    init {
        setEGLContextClientVersion(2)
        setEGLConfigChooser(8, 8, 8, 0, 0, 0)
        preserveEGLContextOnPause = true
        setRenderer(mazeRenderer)
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

private class MazeRenderer(private val settings: Settings, private var notice: Boolean) : GLSurfaceView.Renderer {
    private val rng = Random.Default
    private val renderer = BoardRenderer()
    private var board: Board? = null
    private var buffer: Bitmap? = null
    private var bufferCanvas: Canvas? = null
    private var width = 0
    private var height = 0

    private var program = 0
    private var texture = 0
    private var framebuffer = 0
    private var textureWidth = 0
    private var textureHeight = 0
    private var needsFullUpload = true
    private val uploader = TextureUploader()
    private var lastFrameNanos = 0L

    @Volatile var listener: MazeListener? = null
    private val main = Handler(Looper.getMainLooper())
    private var seenSolved = 0
    private var seenCleared = 0

    /** On the render thread: the current board and any created later. */
    fun setNotice(on: Boolean) {
        notice = on
        board?.notice = on
    }

    private val quad: FloatBuffer = ByteBuffer.allocateDirect(8 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        .apply { put(floatArrayOf(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f)).position(0) }

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        // Display priority, the same class Android gives its own UI thread, so background
        // work on a busy TV does not preempt frames.
        Process.setThreadPriority(Process.THREAD_PRIORITY_DISPLAY)
        // A new context means any earlier program and texture are gone.
        program = buildProgram(VERTEX_SHADER, FRAGMENT_SHADER)
        val ids = IntArray(1)
        GLES20.glGenTextures(1, ids, 0)
        texture = ids[0]
        GLES20.glGenFramebuffers(1, ids, 0)
        framebuffer = ids[0]
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
            // A resize replaces the board. The dream only resizes while the old board is black
            // for its next maze, so the new one starts at once rather than after a random delay.
            val delay = if (board == null) rng.nextDouble(0.0, FIRST_DELAY_MAX) else 0.0
            board = Board(w, h, settings, rng, delay).also { it.notice = notice }
            seenSolved = 0
            seenCleared = 0
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
        val changes = b.update(dt)
        val l = listener
        if (l != null) {
            if (b.mazesSolved != seenSolved) {
                seenSolved = b.mazesSolved
                main.post { l.onMazeSolved() }
            }
            if (b.mazesCleared != seenCleared) {
                seenCleared = b.mazesCleared
                main.post { l.onMazeCleared() }
            }
        }
        val drawn = renderer.apply(bufferCanvas!!, b, b.geometry, changes)
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
        when {
            needsFullUpload -> {
                uploader.upload(buffer!!, Rect(0, 0, width, height))
                needsFullUpload = false
            }
            changes.clear -> clearTexture()
        }
        if (drawn.size > MAX_CELL_UPLOADS) {
            uploader.upload(buffer!!, Rect(drawn[0]).apply { drawn.forEach { union(it) } })
        } else {
            drawn.forEach { uploader.upload(buffer!!, it) }
        }
        drawQuad()
    }

    /** Blacks out the texture on the GPU, matching the cleared bitmap without an upload. */
    private fun clearTexture() {
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, framebuffer)
        GLES20.glFramebufferTexture2D(GLES20.GL_FRAMEBUFFER, GLES20.GL_COLOR_ATTACHMENT0, GLES20.GL_TEXTURE_2D, texture, 0)
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
        GLES20.glBindFramebuffer(GLES20.GL_FRAMEBUFFER, 0)
    }

    private fun drawQuad() {
        GLES20.glUseProgram(program)
        val pos = GLES20.glGetAttribLocation(program, "aPos")
        GLES20.glEnableVertexAttribArray(pos)
        GLES20.glVertexAttribPointer(pos, 2, GLES20.GL_FLOAT, false, 0, quad)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    }
}
