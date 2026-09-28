# Maze Game

Procedurally grown pipe mazes in three forms: a playable game for Windows, a Windows screensaver, and a Google TV screensaver. Each maze is carved live by one or more snake-like leads (up to 12 by default), each in its own color, that race across the screen and weld their regions together into a single perfect maze with exactly one route between any two cells. In the screensavers, a solver then traces that route the way a person would with a finger: it looks a few cells ahead, sometimes takes a wrong turn, backs out of dead ends, and leaves a bright trail behind its gliding dot. The game and the Windows screensaver are Python and pygame; the TV version is a Kotlin port that runs as a native Android screensaver.

## Contents

- [Play](#play)
  - [Difficulty](#difficulty)
- [Add the screensaver](#add-the-screensaver)
- [Google TV screensaver](#google-tv-screensaver)
  - [1. Turn on debugging on the TV](#1-turn-on-debugging-on-the-tv)
  - [2. Connect and install](#2-connect-and-install)
  - [3. Make it the screensaver](#3-make-it-the-screensaver)
  - [Updating and cleanup](#updating-and-cleanup)
  - [Tests](#tests)
- [Develop](#develop)
- [Build](#build)

## Play

Guide a dot from the green start to the red finish. Each maze grows in front of you (or appears instantly), and if you get stuck, Hint lights up the next few cells and Auto-solve takes over from wherever you are.

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

`android/` is a Kotlin port of the screensaver for Google TV and Android TV (Android 8 or newer). It runs as a real Android screensaver (a `DreamService`) and adds a Maze Screensaver app to the TV's app list, with the same settings as the Windows version, a Preview button, and a status line showing whether it is the active screensaver. It is tested on a TCL 65QM6K Pro running Android 14.

Google TV has no store listing for it and hides the screensaver picker, so setup is a one-time sideload from a PC. You need [Android Studio](https://developer.android.com/studio) (for the SDK and `adb`) and the TV on the same network as the PC.

### 1. Turn on debugging on the TV

1. Open **Settings, System, About**, scroll to **Android TV OS build**, and select it 7 times until the TV says you are a developer.
2. Open **Settings, System, Developer options** and turn on **USB debugging**. On Android TV this also opens network debugging on port 5555; **Wireless debugging** is not needed.
3. Note the TV's IP address (**Settings, Network & Internet**, then your connection).

### 2. Connect and install

The commands below are for PowerShell. `adb` ships with Android Studio's SDK, so first point a variable at it:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb connect <tv-ip>:5555
```

The TV shows **Allow USB debugging?** Choose **Always allow from this computer**, then **OK**. `& $adb devices` should now list the TV as `device`, not `unauthorized`.

Build and install from the `android` folder:

```powershell
cd android
.\gradlew.bat installDebug
```

Or open `android/` in Android Studio, pick the TV as the target device, and press Run. If Gradle complains about the Java version, set `JAVA_HOME` to the JDK bundled with Android Studio (`C:\Program Files\Android\Android Studio\jbr`).

### 3. Make it the screensaver

Select it once:

```powershell
& $adb shell settings put secure screensaver_components io.github.tntguerrilla.mazesaver/.MazeDreamService
& $adb shell settings get secure screensaver_components
```

The second command should print `io.github.tntguerrilla.mazesaver/.MazeDreamService`. Then, on the TV:

- **TCL TVs:** allow **Auto Launch** for Maze Screensaver (under **Settings, Apps, Special app access**, or TCL's app permission settings). Without it, TCL's firmware stops the screensaver from starting in the background.
- Open **Maze Screensaver** from the app list. The bottom of the screen should say it is the current screensaver, and **Preview screensaver** shows it right away.

The screensaver starts after the TV's normal screensaver timeout; any remote button ends it. If it never starts on its own, idle screensavers may be switched off on that TV. Check with `& $adb shell settings get secure screensaver_activate_on_sleep`, and if it prints `0`, turn them on:

```powershell
& $adb shell settings put secure screensaver_activate_on_sleep 1
```

### Updating and cleanup

To install a new version, turn USB debugging back on if needed, reconnect with `& $adb connect <tv-ip>:5555`, and run `.\gradlew.bat installDebug` again. The screensaver selection and settings are kept.

Once it is set up, USB debugging can be turned off; the screensaver keeps working without it. While it is on, only computers you have approved can connect.

To go back to Google's Ambient mode, run `& $adb shell settings delete secure screensaver_components`, then uninstall Maze Screensaver from the TV if you no longer want it.

### Tests

Unit tests for the Kotlin port (maze generation, solver, board cycle, settings) run on the PC: `.\gradlew.bat testDebugUnitTest` in `android/`.

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
