# Builds dist\MazeScreensaver.scr with Nuitka (onefile, no console window).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$build = Join-Path $root "build"
$dist = Join-Path $root "dist"

# Unique per build: the onefile cache path below includes the version, so a rebuilt
# .scr never reuses stale unpacked files from an earlier build.
$now = Get-Date
$buildMinute = ($now.Day - 1) * 1440 + $now.Hour * 60 + $now.Minute
$version = "1.0.$($now.ToString('yyMM')).$buildMinute"

& $python -m nuitka `
    --onefile `
    --windows-console-mode=disable `
    --enable-plugins=tk-inter `
    "--onefile-tempdir-spec={CACHE_DIR}/MazeScreensaver/{VERSION}" `
    --product-name="Maze Screensaver" `
    --file-description="Maze Screensaver" `
    --product-version=$version `
    --file-version=$version `
    --assume-yes-for-downloads `
    --output-dir="$build" `
    --output-filename=MazeScreensaver.exe `
    (Join-Path $root "MazeScreensaver.py")
if ($LASTEXITCODE -ne 0) { throw "Nuitka build failed with exit code $LASTEXITCODE" }

New-Item -ItemType Directory -Force $dist | Out-Null
Copy-Item (Join-Path $build "MazeScreensaver.exe") (Join-Path $dist "MazeScreensaver.scr") -Force
Write-Output "Built $(Join-Path $dist 'MazeScreensaver.scr') version $version"
