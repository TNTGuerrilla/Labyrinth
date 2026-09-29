// The game's drawing surface. The GameController lives on GLSurfaceView's render thread;
// the activity reaches it only through send(), and reads what it needs to show from the
// snapshot published every frame.
//
// The maze is drawn into a bitmap in maze space (texCell pixels per cell), with only the
// changed cells uploaded to a GPU texture, as MazeView does. Each frame the texture is
// drawn through the camera (zoom and scroll cost nothing), then the overlays (hint rings,
// finish flash, win pulse, the dot) are drawn with a small circle shader.
package com.bydesigninteractive.labyrinth.play

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Rect
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Process
import com.bydesigninteractive.labyrinth.BoardRenderer
import com.bydesigninteractive.labyrinth.DOT_AT_END_SCALE
import com.bydesigninteractive.labyrinth.END_COLOR
import com.bydesigninteractive.labyrinth.MARKER_RADIUS
import com.bydesigninteractive.labyrinth.START_COLOR
import com.bydesigninteractive.labyrinth.TRAIL_COLOR
import com.bydesigninteractive.labyrinth.TextureUploader
import com.bydesigninteractive.labyrinth.buildProgram
import com.bydesigninteractive.labyrinth.game.Camera
import com.bydesigninteractive.labyrinth.game.FLASH_SECONDS
import com.bydesigninteractive.labyrinth.game.GameController
import com.bydesigninteractive.labyrinth.game.GameSettings
import com.bydesigninteractive.labyrinth.game.HINT_SECONDS
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.game.Round
import com.bydesigninteractive.labyrinth.game.RoundPhase
import com.bydesigninteractive.labyrinth.game.WIN_PULSE_SECONDS
import com.bydesigninteractive.labyrinth.game.gridSize
import com.bydesigninteractive.labyrinth.game.pickShort
import com.bydesigninteractive.labyrinth.maze.Cell
import com.bydesigninteractive.labyrinth.maze.Changes
import com.bydesigninteractive.labyrinth.maze.Geometry
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.random.Random

private const val MAX_FRAME_SECONDS = 0.25
private const val MAX_TEXTURE = 4096
private const val MAX_CELL_UPLOADS = 64
private const val REDRAW_BUDGET_NANOS = 8_000_000L // cell redraws per frame after a full invalidate
private const val REDRAW_CHUNK = 64
private val HINT_COLOR = Color.rgb(120, 200, 255)
private const val ARROW_INSET = 28f // at 720 px of screen height; scaled up on bigger screens
private const val ARROW_SIZE = 14f

/** What the activity shows around the maze, published by the render thread each frame. */
data class Snapshot(
    val phase: RoundPhase,
    val explored: Int,
    val autoExplored: Int,
    val shortest: Int,
    val efficiency: Int,
    val elapsed: Double,
    val hints: Int,
    val assisted: Boolean,
    val timerRunning: Boolean,
    val winScreen: Boolean,
    val dotMoving: Boolean,
)

class GameView(context: Context, settings: GameSettings, remote: RemoteProfile, startPaused: Boolean) :
    GLSurfaceView(context) {
    private val game = GameRenderer(settings, remote, startPaused)

    init {
        setEGLContextClientVersion(2)
        setEGLConfigChooser(8, 8, 8, 0, 0, 0)
        preserveEGLContextOnPause = true
        setRenderer(game)
        renderMode = RENDERMODE_CONTINUOUSLY
    }

    /** Runs [block] on the render thread, where the game lives. */
    fun send(block: GameRenderer.() -> Unit) = queueEvent { game.block() }

    val snapshot: Snapshot? get() = game.snapshot
}

private val MAZE_VERTEX = """
    attribute vec2 aPos;
    uniform vec2 uOrigin;
    uniform vec2 uSize;
    uniform vec2 uScreen;
    varying highp vec2 vUv;
    void main() {
        vec2 p = uOrigin + aPos * uSize;
        vUv = aPos;
        gl_Position = vec4(p.x / uScreen.x * 2.0 - 1.0, 1.0 - p.y / uScreen.y * 2.0, 0.0, 1.0);
    }
""".trimIndent()

// The texture holds B, G, R, A bytes (see TextureUploader), so red and blue swap back.
private val MAZE_FRAGMENT = """
    precision mediump float;
    uniform sampler2D uTex;
    varying highp vec2 vUv;
    void main() {
        gl_FragColor = vec4(texture2D(uTex, vUv).bgr, 1.0);
    }
""".trimIndent()

private val CIRCLE_VERTEX = """
    attribute vec2 aPos;
    uniform vec2 uCenter;
    uniform mediump float uRadius; // must match the fragment shader's precision to link
    uniform vec2 uScreen;
    varying vec2 vLocal;
    void main() {
        vLocal = aPos * (uRadius + 1.0);
        vec2 p = uCenter + vLocal;
        gl_Position = vec4(p.x / uScreen.x * 2.0 - 1.0, 1.0 - p.y / uScreen.y * 2.0, 0.0, 1.0);
    }
""".trimIndent()

// A filled circle, or a ring when uInner > 0, with a one-pixel soft edge.
private val CIRCLE_FRAGMENT = """
    precision mediump float;
    uniform float uRadius;
    uniform float uInner;
    uniform vec4 uColor;
    varying vec2 vLocal;
    void main() {
        float d = length(vLocal);
        float a = clamp(uRadius + 0.5 - d, 0.0, 1.0);
        if (uInner > 0.0) a *= clamp(d - uInner + 0.5, 0.0, 1.0);
        gl_FragColor = vec4(uColor.rgb, uColor.a * a);
    }
""".trimIndent()

private val TRIANGLE_VERTEX = """
    attribute vec2 aPos;
    uniform vec2 uScreen;
    void main() {
        gl_Position = vec4(aPos.x / uScreen.x * 2.0 - 1.0, 1.0 - aPos.y / uScreen.y * 2.0, 0.0, 1.0);
    }
""".trimIndent()

private val TRIANGLE_FRAGMENT = """
    precision mediump float;
    uniform vec4 uColor;
    void main() {
        gl_FragColor = uColor;
    }
""".trimIndent()

private fun floats(vararg v: Float): FloatBuffer =
    ByteBuffer.allocateDirect(v.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().apply { put(v).position(0) }

class GameRenderer(settings: GameSettings, remote: RemoteProfile, startPaused: Boolean) : GLSurfaceView.Renderer {
    var settings = settings
        private set
    private val controller = GameController(settings, remote)
    /** While true (the menu is open, or the app is away) the game does not advance. */
    var paused = startPaused
        set(value) {
            field = value
            lastFrameNanos = 0L
        }
    @Volatile var snapshot: Snapshot? = null
        private set

    private val rng = Random.Default
    private val cellRenderer = BoardRenderer()
    private val uploader = TextureUploader()
    private var started = false
    private var camera: Camera? = null
    private var bitmap: Bitmap? = null
    private var canvas: Canvas? = null
    private var texCell = 1
    private var width = 0
    private var height = 0
    private var maxTextureSize = MAX_TEXTURE
    private var texture = 0
    private var textureReady = false
    private val redraw = ArrayDeque<Cell>()
    private var lastFrameNanos = 0L

    private var mazeProgram = 0
    private var circleProgram = 0
    private var triangleProgram = 0
    private val unitQuad = floats(0f, 0f, 1f, 0f, 0f, 1f, 1f, 1f)
    private val centeredQuad = floats(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f)
    private val triangle = ByteBuffer.allocateDirect(6 * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()

    private val round: Round get() = controller.round

    // --- commands (render thread) ----------------------------------------------------

    fun newRound() {
        val s = settings
        val short = pickShort(s.size, s.customMin, s.customMax, width, height, rng)
        val (cols, rows) = gridSize(short, width, height)
        val r = Round.create(cols, rows, s, rng)
        controller.start(r)
        val cam = Camera(cols, rows, width, height)
        cam.zoomBy(s.zoomSteps, (r.start.x + 0.5) to (r.start.y + 0.5))
        camera = cam
        texCell = max(1, min(cam.maxPx, min(MAX_TEXTURE, maxTextureSize) / max(cols, rows)))
        bitmap?.recycle()
        val bmp = Bitmap.createBitmap(cols * texCell, rows * texCell, Bitmap.Config.ARGB_8888)
        bitmap = bmp
        canvas = Canvas(bmp).apply { drawColor(Color.BLACK) }
        redraw.clear()
        textureReady = false
        started = true
    }

    fun replay() {
        controller.replay()
        camera?.let {
            it.resetZoom()
            it.zoomBy(settings.zoomSteps, round.mover.position())
        }
        redrawAll()
    }

    fun applySettings(s: GameSettings) {
        val old = settings
        settings = s
        controller.settings = s
        if (!started) return
        if (old.multicolor != s.multicolor) {
            round.multicolor = s.multicolor
            redrawAll()
        }
        if (old.showGrid != s.showGrid) redrawAll()
        if (old.zoomSteps != s.zoomSteps) {
            camera?.let {
                it.resetZoom()
                it.zoomBy(s.zoomSteps, round.mover.position())
            }
        }
    }

    fun setRemote(p: RemoteProfile) {
        controller.remote = p
    }

    fun pressArrow(d: Int) = controller.pressArrow(d)
    fun releaseArrow(d: Int) = controller.releaseArrow(d)
    fun skipGrowth() = controller.skipGrowth()
    fun hint() = controller.hint()
    fun flash() = controller.flash()
    fun toggleAuto() = controller.toggleAuto()

    /** Key-ups can be lost while the app is away, so held arrows are forgotten. */
    fun clearKeys() = controller.keys.clear()

    private fun redrawAll() {
        redraw.clear()
        round.grid.cells().forEach { redraw.add(it) }
    }

    // --- GLSurfaceView.Renderer ------------------------------------------------------------

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        Process.setThreadPriority(Process.THREAD_PRIORITY_DISPLAY)
        mazeProgram = buildProgram(MAZE_VERTEX, MAZE_FRAGMENT)
        circleProgram = buildProgram(CIRCLE_VERTEX, CIRCLE_FRAGMENT)
        triangleProgram = buildProgram(TRIANGLE_VERTEX, TRIANGLE_FRAGMENT)
        val v = IntArray(1)
        GLES20.glGetIntegerv(GLES20.GL_MAX_TEXTURE_SIZE, v, 0)
        maxTextureSize = v[0]
        GLES20.glGenTextures(1, v, 0)
        texture = v[0]
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
        for ((name, value) in listOf(
            GLES20.GL_TEXTURE_MIN_FILTER to GLES20.GL_LINEAR,
            GLES20.GL_TEXTURE_MAG_FILTER to GLES20.GL_LINEAR,
            GLES20.GL_TEXTURE_WRAP_S to GLES20.GL_CLAMP_TO_EDGE,
            GLES20.GL_TEXTURE_WRAP_T to GLES20.GL_CLAMP_TO_EDGE,
        )) GLES20.glTexParameteri(GLES20.GL_TEXTURE_2D, name, value)
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA)
        // A new context means the old texture is gone; onDrawFrame uploads the bitmap again.
        textureReady = false
        lastFrameNanos = 0L
    }

    override fun onSurfaceChanged(gl: GL10?, w: Int, h: Int) {
        GLES20.glViewport(0, 0, w, h)
        val first = !started
        width = w
        height = h
        if (first) newRound() else camera?.resize(w, h)
    }

    override fun onDrawFrame(gl: GL10?) {
        if (!started) return
        val bmp = bitmap ?: return
        GLES20.glBindTexture(GLES20.GL_TEXTURE_2D, texture)
        if (!textureReady) {
            GLES20.glTexImage2D(GLES20.GL_TEXTURE_2D, 0, GLES20.GL_RGBA, bmp.width, bmp.height, 0,
                GLES20.GL_RGBA, GLES20.GL_UNSIGNED_BYTE, null)
            uploader.upload(bmp, Rect(0, 0, bmp.width, bmp.height))
            textureReady = true
        }
        val now = System.nanoTime()
        val dt = if (lastFrameNanos == 0L) 0.0 else ((now - lastFrameNanos) / 1e9).coerceIn(0.0, MAX_FRAME_SECONDS)
        lastFrameNanos = now
        val cam = camera!!
        val changed = if (paused) emptySet() else controller.frame(dt)
        if (!paused) cam.follow(round.mover.position(), dt)
        drawCells(bmp, changed)
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
        drawMaze(cam)
        GLES20.glEnable(GLES20.GL_BLEND)
        drawOverlays(cam)
        GLES20.glDisable(GLES20.GL_BLEND)
        publish()
    }

    // --- drawing ---------------------------------------------------------------------------

    private fun drawCells(bmp: Bitmap, changed: Set<Cell>) {
        val c = canvas ?: return
        val r = round
        val geo = Geometry(r.grid.cols, r.grid.rows, texCell, 0, 0)
        val grid = settings.showGrid
        val drawn = ArrayList<Rect>()
        if (changed.isNotEmpty()) {
            val changes = Changes()
            changes.cells.addAll(changed)
            drawn += cellRenderer.apply(c, r, geo, changes, drawDot = false, gridLines = grid)
        }
        val deadline = System.nanoTime() + REDRAW_BUDGET_NANOS
        while (redraw.isNotEmpty() && System.nanoTime() < deadline) {
            val chunk = Changes()
            repeat(REDRAW_CHUNK) { redraw.removeFirstOrNull()?.let { chunk.cells.add(it) } }
            drawn += cellRenderer.apply(c, r, geo, chunk, drawDot = false, gridLines = grid)
        }
        if (drawn.size > MAX_CELL_UPLOADS) {
            uploader.upload(bmp, Rect(drawn[0]).apply { drawn.forEach { union(it) } })
        } else {
            drawn.forEach { uploader.upload(bmp, it) }
        }
    }

    private fun drawMaze(cam: Camera) {
        val p = mazeProgram
        GLES20.glUseProgram(p)
        val (ox, oy) = cam.origin()
        GLES20.glUniform2f(GLES20.glGetUniformLocation(p, "uOrigin"), ox.toFloat(), oy.toFloat())
        GLES20.glUniform2f(GLES20.glGetUniformLocation(p, "uSize"),
            (cam.cols * cam.cellPx).toFloat(), (cam.rows * cam.cellPx).toFloat())
        GLES20.glUniform2f(GLES20.glGetUniformLocation(p, "uScreen"), width.toFloat(), height.toFloat())
        val pos = GLES20.glGetAttribLocation(p, "aPos")
        GLES20.glEnableVertexAttribArray(pos)
        GLES20.glVertexAttribPointer(pos, 2, GLES20.GL_FLOAT, false, 0, unitQuad)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    }

    private fun circle(x: Double, y: Double, radius: Float, inner: Float, color: Int, alpha: Float) {
        val p = circleProgram
        GLES20.glUseProgram(p)
        GLES20.glUniform2f(GLES20.glGetUniformLocation(p, "uCenter"), x.toFloat(), y.toFloat())
        GLES20.glUniform1f(GLES20.glGetUniformLocation(p, "uRadius"), radius)
        GLES20.glUniform1f(GLES20.glGetUniformLocation(p, "uInner"), inner)
        GLES20.glUniform2f(GLES20.glGetUniformLocation(p, "uScreen"), width.toFloat(), height.toFloat())
        GLES20.glUniform4f(GLES20.glGetUniformLocation(p, "uColor"),
            Color.red(color) / 255f, Color.green(color) / 255f, Color.blue(color) / 255f, alpha.coerceIn(0f, 1f))
        val pos = GLES20.glGetAttribLocation(p, "aPos")
        GLES20.glEnableVertexAttribArray(pos)
        GLES20.glVertexAttribPointer(pos, 2, GLES20.GL_FLOAT, false, 0, centeredQuad)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
    }

    private fun ring(x: Double, y: Double, radius: Float, width: Float, color: Int, alpha: Float) =
        circle(x, y, radius, max(0.01f, radius - width), color, alpha)

    /** The overlays of maze_game/game_render.py's draw_overlays. */
    private fun drawOverlays(cam: Camera) {
        val r = round
        val px = cam.cellPx
        fun center(c: Cell) = cam.toScreen(c.x + 0.5, c.y + 0.5)
        val radius = max(3, (px * MARKER_RADIUS).roundToInt()).toFloat()
        val hintAt = r.hintAt
        if (r.hintActive && hintAt != null) {
            val age = r.time - hintAt
            val fade = 1.0 - age / HINT_SECONDS
            val pulse = 0.65 + 0.35 * sin(age * 2 * PI * 2)
            val size = max(2, (px * 0.42).roundToInt()).toFloat()
            for (c in r.hintRoute) {
                val (x, y) = center(c)
                ring(x, y, size, max(1, px / 8).toFloat(), HINT_COLOR, (fade * pulse).toFloat())
            }
        }
        val wonAt = r.wonAt
        if (r.winPulseActive && wonAt != null) {
            val b = sin(PI * min(1.0, (r.time - wonAt) / WIN_PULSE_SECONDS))
            val color = mix(TRAIL_COLOR, Color.WHITE, b)
            val size = max(1, (px * 0.2 * (1 + b)).roundToInt()).toFloat()
            for (c in r.path.route) {
                val (x, y) = center(c)
                circle(x, y, size, 0f, color, 1f)
            }
        }
        val flashAt = r.flashAt
        if (r.flashActive && flashAt != null) {
            val t = (r.time - flashAt) / FLASH_SECONDS
            val (ex, ey) = center(r.end)
            val reach = max(px * 2.5, 36.0)
            for (i in 0 until 3) {
                val phase = (t * 2 + i / 3.0) % 1.0
                ring(ex, ey, (radius + phase * reach).toFloat(), 2f, END_COLOR, ((1 - phase) * (1 - t)).toFloat())
            }
            if (ex < 0 || ey < 0 || ex > width || ey > height) arrow(ex, ey, (1 - t * 0.5).toFloat())
        }
        val (dx, dy) = cam.toScreen(r.mover.position().first, r.mover.position().second)
        val dotRadius = if (r.dot == r.end && !r.mover.moving) max(1f, radius * DOT_AT_END_SCALE.toFloat()) else radius
        circle(dx, dy, dotRadius, 0f, START_COLOR, 1f)
    }

    /** A triangle at the screen edge pointing from the center toward (tx, ty). */
    private fun arrow(tx: Double, ty: Double, alpha: Float) {
        val scale = height / 720.0
        val cx = width / 2.0
        val cy = height / 2.0
        val vx = tx - cx
        val vy = ty - cy
        val length = hypot(vx, vy)
        if (length == 0.0) return
        val ux = vx / length
        val uy = vy / length
        val hw = width / 2.0 - ARROW_INSET * scale
        val hh = height / 2.0 - ARROW_INSET * scale
        val reach = min(if (ux != 0.0) hw / abs(ux) else Double.MAX_VALUE, if (uy != 0.0) hh / abs(uy) else Double.MAX_VALUE)
        val tipX = cx + ux * reach
        val tipY = cy + uy * reach
        val size = ARROW_SIZE * scale
        val baseX = tipX - ux * size * 1.6
        val baseY = tipY - uy * size * 1.6
        triangle.clear()
        triangle.put(floatArrayOf(
            tipX.toFloat(), tipY.toFloat(),
            (baseX - uy * size).toFloat(), (baseY + ux * size).toFloat(),
            (baseX + uy * size).toFloat(), (baseY - ux * size).toFloat(),
        )).position(0)
        val p = triangleProgram
        GLES20.glUseProgram(p)
        GLES20.glUniform2f(GLES20.glGetUniformLocation(p, "uScreen"), width.toFloat(), height.toFloat())
        GLES20.glUniform4f(GLES20.glGetUniformLocation(p, "uColor"),
            Color.red(END_COLOR) / 255f, Color.green(END_COLOR) / 255f, Color.blue(END_COLOR) / 255f, alpha)
        val pos = GLES20.glGetAttribLocation(p, "aPos")
        GLES20.glEnableVertexAttribArray(pos)
        GLES20.glVertexAttribPointer(pos, 2, GLES20.GL_FLOAT, false, 0, triangle)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLES, 0, 3)
    }

    private fun mix(a: Int, b: Int, k: Double): Int {
        fun ch(x: Int, y: Int) = (x + (y - x) * k).toInt()
        return Color.rgb(ch(Color.red(a), Color.red(b)), ch(Color.green(a), Color.green(b)), ch(Color.blue(a), Color.blue(b)))
    }

    private fun publish() {
        val r = round
        snapshot = Snapshot(
            r.phase, r.explored, r.autoExplored, r.shortest, r.efficiency, r.elapsed, r.hints, r.assisted,
            r.timerRunning, r.winOverlayVisible, controller.dotMoving,
        )
    }
}
