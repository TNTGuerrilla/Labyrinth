package com.bydesigninteractive.labyrinth.play

import android.app.Activity
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import com.bydesigninteractive.labyrinth.game.RemoteProfile
import com.bydesigninteractive.labyrinth.maze.E
import com.bydesigninteractive.labyrinth.maze.N
import com.bydesigninteractive.labyrinth.maze.S
import com.bydesigninteractive.labyrinth.maze.W

class GameActivity : Activity() {
    private lateinit var view: GameView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        view = GameView(this, GameStore.load(this), GameStore.loadRemote(this) ?: RemoteProfile(), startPaused = false)
        view.systemUiVisibility = View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        setContentView(view)
    }

    override fun onResume() {
        super.onResume()
        view.onResume()
    }

    override fun onPause() {
        view.onPause()
        super.onPause()
    }

    private fun arrow(keyCode: Int): Int? = when (keyCode) {
        KeyEvent.KEYCODE_DPAD_UP -> N
        KeyEvent.KEYCODE_DPAD_RIGHT -> E
        KeyEvent.KEYCODE_DPAD_DOWN -> S
        KeyEvent.KEYCODE_DPAD_LEFT -> W
        else -> null
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK) {
            finish()
            return true
        }
        val d = arrow(keyCode) ?: return super.onKeyDown(keyCode, event)
        if (event.repeatCount == 0) view.send { pressArrow(d) }
        return true
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        val d = arrow(keyCode) ?: return super.onKeyUp(keyCode, event)
        view.send { releaseArrow(d) }
        return true
    }
}
