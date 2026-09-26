# Maze Screensaver

A Windows screensaver. On every monitor a pipe-style maze grows around a green start dot and a red end dot, a dot solves it while leaving a trail (dead ends fade, the true path stays bright), the solved maze holds for a moment, then the screen cuts to black and a new maze begins.

## Install

Build it (below), then right-click `dist\MazeScreensaver.scr` and choose **Install**. Pick "MazeScreensaver" in Screen Saver Settings. The Settings button there controls maze density, speeds, hold time and frame rate cap.

## Develop

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements-dev.txt
    .venv\Scripts\python -m pytest
    .venv\Scripts\python -m maze_saver --window       # scaled debug view of all monitors
    .venv\Scripts\python -m maze_saver /s             # real screensaver
    .venv\Scripts\python -m maze_saver /s --multiwindow
    .venv\Scripts\python -m maze_saver /c             # settings dialog

## Build

    powershell -ExecutionPolicy Bypass -File .\build.ps1

Output: `dist\MazeScreensaver.scr`. Unexpected errors are logged to `%APPDATA%\MazeScreensaver\error.log`.
