# Labyrinth

<img src="maze_saver/assets/icon.png" alt="Labyrinth icon" width="96" align="right">

Procedurally grown pipe mazes in three forms: a playable game for Windows and Linux, a Windows screensaver, and a Google TV screensaver. Each maze is carved live by one or more snake-like leads (up to 16), each in its own color, that race across the screen and weld their regions together into a single perfect maze with exactly one route between any two cells. In the screensavers, a solver then traces that route the way a person would with a finger: it looks a few cells ahead, sometimes takes a wrong turn, backs out of dead ends, and leaves a bright trail behind its gliding dot. The game and the Windows screensaver are Python and pygame; the TV version is a Kotlin port that runs as a native Android screensaver.

## Contents

- [Download](#download)
- [Updates](#updates)
- [Play](#play)
  - [Difficulty](#difficulty)
  - [Install on Linux](#install-on-linux)
- [Windows screensaver](#windows-screensaver)
- [Google TV screensaver](#google-tv-screensaver)
  - [1. Turn on debugging on the TV](#1-turn-on-debugging-on-the-tv)
  - [2. Connect and install](#2-connect-and-install)
  - [3. Make it the screensaver](#3-make-it-the-screensaver)
  - [Updating and cleanup](#updating-and-cleanup)
- [Build from source](#build-from-source)
  - [Windows game and screensaver](#windows-game-and-screensaver)
  - [Linux game](#linux-game)
  - [Icons](#icons)
  - [Google TV app](#google-tv-app)
- [Develop](#develop)
- [License](#license)

## Download

Each product has its own releases on the [Releases page](https://github.com/TNTGuerrilla/Labyrinth/releases):

| Product | File | Runs on |
|---|---|---|
| Labyrinth (the game) | `Labyrinth.exe` | Windows 10 or 11, 64-bit |
| Labyrinth (the game) | `Labyrinth-<version>-linux-x86_64.tar.gz` | 64-bit Linux with glibc 2.35 or newer (Ubuntu 22.04, Debian 12, Fedora 36 and later) |
| Labyrinth Screensaver | `Labyrinth.scr` | Windows 10 or 11, 64-bit |
| Labyrinth TV | `LabyrinthTV.apk` | Google TV and Android TV, Android 8 or newer |

The Windows files are single programs with nothing to install. Windows SmartScreen may warn about them because they are not code-signed; choose **More info**, then **Run anyway**.

## Updates

Each program checks GitHub for a newer version once a week (and right away the first time it
runs). Only the list of Labyrinth releases is requested; nothing about you or your computer is
sent. Every download is checked against the SHA-256 GitHub publishes for it before it replaces
anything.

- **Labyrinth:** an **Update to X.Y.Z** button appears at the right end of the toolbar. Click it
  to download the new version and restart into it, or click **x** to hide that version.
- **Labyrinth Screensaver:** a dim note appears in a corner of your main monitor while it runs.
  Open **Screen Saver Settings**, choose **Settings**, and click **Update**. If the screensaver is
  in `C:\Windows\System32`, Windows asks for administrator permission first.
- **Labyrinth TV:** a note appears on the screensaver, and the Labyrinth app shows **Update**.
  The first time, Android asks you to allow Labyrinth to install apps.

After an update, each program says once what changed: Labyrinth shows a **What's new** panel,
the screensaver shows a quiet section beside the maze for a minute or so, and the TV app shows
the notes at the top of its settings screen (or the TV screensaver shows them beside the maze).

Each program's settings also have an **Info** section with its version, the project's GitHub
page and license, **Check now** (which works even with weekly checks turned off) and
**What's new**.

To turn checks off, use the check toggle in each program's settings: Labyrinth's Settings, Info
tab (**Check for updates weekly**); the screensaver's Screen Saver Settings dialog, Info section
(**Check for updates weekly**); the TV app's settings screen (**Check for updates: On/Off**).

Versions released before this feature (Labyrinth 1.1.0, Labyrinth Screensaver 1.0.1 and
Labyrinth TV 1.0.0) cannot update themselves. Download the next version once by hand; after
that, updates happen in the app.

### A note on administrator updates

This is general background about Windows, not something unique to Labyrinth.

When the screensaver is in `C:\Windows\System32`, Windows asks for administrator permission before it updates, and the update step then runs with administrator rights. Like most Windows programs that unpack themselves to run, including many installers, part of it runs from a folder in your user profile. If harmful software were already running under your Windows account, it could tamper with that folder and gain administrator rights when you approve the prompt. Microsoft does not treat this as a security boundary, since software running as you has other ways to do the same. The usual advice applies: keep your PC free of malware, and only approve permission prompts you started yourself.

To avoid administrator prompts entirely, keep `Labyrinth.scr` in a folder you own (for example `%LOCALAPPDATA%\Programs\Labyrinth`) and install it from there. It then updates without asking.

## Play

Guide a dot from the green start to the red finish. Each maze grows in front of you (or appears instantly), and if you get stuck, Hint lights up the next few cells and Auto-solve takes over from wherever you are.

Run `Labyrinth.exe` (on Linux, see [Install on Linux](#install-on-linux)). Hold a direction to glide; the dot follows corridor bends on its own and stops at forks and dead ends. Walking back over your trail dims it, so the bright line is always your route from the start.

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

### Install on Linux

Unpack the download and run its installer, which puts the game in `~/.local/bin/labyrinth` and adds it to your app menu with its icon:

```bash
tar -xzf Labyrinth-*-linux-x86_64.tar.gz
cd Labyrinth-*-linux-x86_64
./install.sh
```

Nothing needs root. To run it without installing, start `./Labyrinth` from the unpacked folder instead. `./install.sh --uninstall` removes it again. Settings are stored in `~/.config/Labyrinth` (or `$XDG_CONFIG_HOME/Labyrinth`), with any `error.log` next to them.

The screensaver is Windows only. Linux desktops have no common screensaver system for it to plug into.

## Windows screensaver

The screensaver is a separate download from the game:

1. Right-click `Labyrinth.scr` and choose **Install**.
2. In Screen Saver Settings, pick **Labyrinth**. Its Settings button controls maze density, speeds, hold time and the frame rate cap.

If **Install** is missing from the right-click menu, another program has claimed `.scr` files (AutoCAD does this). Copy `Labyrinth.scr` into `C:\Windows\System32` instead, then pick it in Screen Saver Settings.

## Google TV screensaver

Labyrinth TV runs as a real Android screensaver and adds a **Labyrinth** app to the TV's app list, with the same settings as the Windows version, a Preview button, and a status line showing whether it is the active screensaver. It is tested on a TCL 65QM6K Pro running Android 14.

Google TV has no store listing for it and hides the screensaver picker, so setup is a one-time sideload from a PC. You need `adb`, from Google's [SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) (also included with Android Studio), and the TV on the same network as the PC.

### 1. Turn on debugging on the TV

1. Open **Settings, System, About**, scroll to **Android TV OS build**, and select it 7 times until the TV says you are a developer.
2. Open **Settings, System, Developer options** and turn on **USB debugging**. On Android TV this also opens network debugging on port 5555; **Wireless debugging** is not needed.
3. Note the TV's IP address (**Settings, Network & Internet**, then your connection).

### 2. Connect and install

The commands below are for PowerShell. Point a variable at `adb` (this is where Android Studio puts it; use your Platform-Tools folder otherwise) and connect:

```powershell
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb connect <tv-ip>:5555
```

The TV shows **Allow USB debugging?** Choose **Always allow from this computer**, then **OK**. `& $adb devices` should now list the TV as `device`, not `unauthorized`.

Install the downloaded APK:

```powershell
& $adb install LabyrinthTV.apk
```

To install a build of your own instead, see [Google TV app](#google-tv-app).

### 3. Make it the screensaver

Select it once:

```powershell
& $adb shell settings put secure screensaver_components com.bydesigninteractive.labyrinth/.LabyrinthDreamService
& $adb shell settings get secure screensaver_components
```

The second command should print `com.bydesigninteractive.labyrinth/.LabyrinthDreamService`.

**TCL TVs** also need this. TCL's firmware blocks screensavers from starting unless the app is allowed to launch itself (TCL's Auto Launch setting, which is hard to find), and this grants it:

```powershell
& $adb shell appops set com.bydesigninteractive.labyrinth AUTO_START allow
```

Then, on the TV:

- Open **Labyrinth** from the app list. The bottom of the screen should say it is the current screensaver, and **Preview screensaver** shows it right away.

The screensaver starts after the TV's normal screensaver timeout; any remote button ends it. If it never starts on its own, idle screensavers may be switched off on that TV. Check with `& $adb shell settings get secure screensaver_activate_on_sleep`, and if it prints `0`, turn them on:

```powershell
& $adb shell settings put secure screensaver_activate_on_sleep 1
```

### Updating and cleanup

Versions with in-app updates update themselves from the Labyrinth app (see [Updates](#updates)). Versions released before in-app updates (Labyrinth TV 1.0.0) update with adb: turn USB debugging back on if needed, reconnect with `& $adb connect <tv-ip>:5555`, and run `& $adb install -r LabyrinthTV.apk` with the new file. The screensaver selection and settings are kept.

Once it is set up, USB debugging can be turned off; the screensaver keeps working without it. While it is on, only computers you have approved can connect.

To go back to Google's Ambient mode, run `& $adb shell settings delete secure screensaver_components`, then uninstall Labyrinth from the TV if you no longer want it.

## Build from source

Product versions live in `versions.json`; both builds read them from there.

### Windows game and screensaver

You need Windows 10 or 11 (64-bit), [Python 3.10](https://www.python.org/downloads/) (the builds use 3.10.11), and a C compiler for Nuitka. If Visual Studio Build Tools are installed, Nuitka uses them; otherwise it downloads a MinGW compiler on the first build.

```powershell
git clone https://github.com/TNTGuerrilla/Labyrinth.git
cd Labyrinth
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

The build takes several minutes and writes `dist\Labyrinth.exe` and `dist\Labyrinth.scr`. Each build gets a unique file version (the product version plus a build number), so the unpack caches under `%LOCALAPPDATA%\Labyrinth` and `%LOCALAPPDATA%\LabyrinthScreensaver` never run stale files; old version folders there can be deleted.

Settings are stored in `%APPDATA%\Labyrinth` (game) and `%APPDATA%\Labyrinth Screensaver` (screensaver), and unexpected errors are logged to `error.log` next to them. Settings from the builds released before the Labyrinth name (in `%APPDATA%\MazeGame` and `%APPDATA%\MazeScreensaver`) are copied over automatically on first run.

### Linux game

On Ubuntu or Debian, install Python with its headers, a C compiler and `patchelf`, then build. WSL works too.

```bash
sudo apt install python3 python3-dev python3-venv gcc patchelf
git clone https://github.com/TNTGuerrilla/Labyrinth.git
cd Labyrinth
python3 -m venv .venv-linux
.venv-linux/bin/pip install -r requirements-dev.txt zstandard
.venv-linux/bin/python -m pytest
PYTHON=.venv-linux/bin/python ./build.sh
```

The build writes `dist/Labyrinth-<version>-linux-x86_64.tar.gz`. The program only runs on distros whose glibc is at least as new as the build machine's, so release builds are made on Ubuntu 22.04. The [Linux build](.github/workflows/linux.yml) workflow does this on GitHub for every push. For a `labyrinth-v*` tag, it attaches the tarball to that tag's release if the release already exists. Otherwise, download the tarball from the run's artifacts.

### Icons

Every product uses the Labyrinth TV launcher icon. `python tools/make_icons.py` (it needs Pillow) turns it into `maze_saver/assets/icon.png`, the window and Linux app icon, and `packaging/labyrinth.ico`, which the Windows build embeds in both programs. Run it again after changing the TV icon.

### Google TV app

You need [Android Studio](https://developer.android.com/studio) (it brings the Android SDK and a JDK), or JDK 17 with the Android SDK platform 35. If Gradle complains about the Java version, set `JAVA_HOME` to the JDK bundled with Android Studio (`C:\Program Files\Android\Android Studio\jbr`).

For a build to try out, with the TV connected over `adb` as above:

```powershell
cd android
.\gradlew.bat installDebug
```

Or open `android/` in Android Studio, pick the TV as the target device, and press Run.

For a release build, create a signing key once, keep it and its passwords somewhere safe, and never commit them:

```powershell
keytool -genkeypair -v -keystore labyrinth-release.jks -alias labyrinth -keyalg RSA -keysize 4096 -validity 36500
```

`keytool` comes with the JDK (Android Studio's is in `jbr\bin`). Copy `android/keystore.properties.example` to `android/keystore.properties`, fill in the key's path and passwords, then build:

```powershell
.\gradlew.bat assembleRelease
```

The signed APK is `android/app/build/outputs/apk/release/app-release.apk`. Without `keystore.properties`, the release build comes out unsigned (`app-release-unsigned.apk`), which Android will not install. Android only installs an update signed with the same key as the installed app, so an app built with a different key has to be uninstalled first.

## Develop

Release notes come from the GitHub release text. Everything above a line that is exactly `---`
is shown in the programs; put the SHA-256 line and install steps below it.
`tools/fake_release_server.py --notes "TAG=TEXT"` serves notes for local tests (`\n` is a line
break).

    .venv\Scripts\python -m pytest
    .venv\Scripts\python -m maze_game                  # the game
    .venv\Scripts\python -m maze_saver --window       # screensaver: scaled debug view of all monitors
    .venv\Scripts\python -m maze_saver /s             # screensaver: real mode
    .venv\Scripts\python -m maze_saver /s --multiwindow
    .venv\Scripts\python -m maze_saver /c             # screensaver settings dialog
    .venv\Scripts\python -m maze_saver --window --leads 8   # force every maze to 8 leads

Unit tests for the TV app's Kotlin port (maze generation, solver, board cycle, settings) run on the PC: `.\gradlew.bat testDebugUnitTest` in `android/`.

## License

Copyright 2026 ByDesign Interactive. Licensed under the [Apache License, Version 2.0](LICENSE). The Windows builds bundle third-party libraries under their own licenses, including pygame-ce under the LGPL 2.1; the Linux build bundles the same libraries. See [NOTICE](NOTICE).
