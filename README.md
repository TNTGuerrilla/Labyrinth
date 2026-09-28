# Maze Game

Guide a dot from the green start to the red finish through procedurally grown pipe mazes. Each maze grows in front of you (or appears instantly), and if you get stuck, Hint lights up the next few cells and Auto-solve takes over from wherever you are. The same mazes also come as a Windows screensaver add-on.

## Play

Run `MazeGame.exe`. Hold a direction to glide; the dot follows corridor bends on its own and stops at forks and dead ends. Walking back over your trail dims it, so the bright line is always your route from the start.

| Action | Default key |
|---|---|
| Move | W A S D or arrow keys |
| Hint | Q |
| Auto-solve (toggle) | E |
| Flash the finish | F |
| New maze | R |
| Replay this maze | T |
| Skip growth, or New maze on the win screen | Space |
| Small, Medium, Large, XL maze | 1, 2, 3, 4 |
| Custom size | 5 |
| Multi-color on/off | C |
| Zoom in, out, reset | +, -, Z (or the mouse wheel) |
| Settings | Esc |
| Fullscreen | F11 |

Mouse: hold the left button to steer the dot toward the cursor (it never passes through walls). Click a cell in a straight open line from the dot to dash there.

Every key can be changed in Settings, Controls tab.

### Difficulty

Small is 8-12 cells on the short side, Medium 13-24, Large 25-48 and XL 49-96; each new maze picks a size in its range. Custom (key 5) takes any size. Its Run benchmark button measures what your PC handles smoothly and estimates how long huge mazes take to build.

The win screen compares your steps with the perfect route. Steps taken by Auto-solve are counted separately and mark the round Assisted.

## Add the screensaver

The mazes are also available as a Windows screensaver, installed separately from the game:

1. Right-click `MazeScreensaver.scr` and choose **Install**.
2. In Screen Saver Settings pick "MazeScreensaver". Its Settings button controls maze density, speeds, hold time and frame rate cap.

## Google TV screensaver

`android/` is a Kotlin port of the screensaver for Google TV and Android TV. It runs as an Android screensaver (a `DreamService`), with a settings screen in the app list.

1. On the TV, open Settings, System, About and select "Android TV OS build" 7 times to unlock Developer options. Then turn on USB debugging there.
2. From the PC: `adb connect <tv-ip>:5555` and accept the prompt on the TV.
3. Build and install: `cd android` then `.\gradlew.bat installDebug` (or Run in Android Studio).
4. Google TV hides the screensaver picker, so select it with ADB once:

       adb shell settings put secure screensaver_components io.github.tntguerrilla.mazesaver/.MazeDreamService

5. On TCL TVs, allow Auto Launch for Maze Screensaver so it can start while the TV is idle.
6. If it still never starts on its own, the TV may have idle screensavers switched off. Turn them on with `adb shell settings put secure screensaver_activate_on_sleep 1`.

The app's settings screen shows whether it is the current screensaver and has a Preview button. Unit tests: `.\gradlew.bat testDebugUnitTest`.

## Develop

    python -m venv .venv
    .venv\Scripts\python -m pip install -r requirements-dev.txt
    .venv\Scripts\python -m pytest
    .venv\Scripts\python -m maze_game                  # the game
    .venv\Scripts\python -m maze_saver --window       # screensaver: scaled debug view of all monitors
    .venv\Scripts\python -m maze_saver /s             # screensaver: real mode
    .venv\Scripts\python -m maze_saver /s --multiwindow
    .venv\Scripts\python -m maze_saver /c             # screensaver settings dialog
    .venv\Scripts\python -m maze_saver --window --leads 8   # force every maze to 8 leads

## Build

    powershell -ExecutionPolicy Bypass -File .\build.ps1

Output: `dist\MazeGame.exe` and `dist\MazeScreensaver.scr`. Unexpected errors are logged to `%APPDATA%\MazeGame\error.log` (game) and `%APPDATA%\MazeScreensaver\error.log` (screensaver). Each build gets a unique version so the unpack caches under `%LOCALAPPDATA%\MazeGame` and `%LOCALAPPDATA%\MazeScreensaver` never run stale files; old version folders there can be deleted.
