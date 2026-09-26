# Builds dist\MazeScreensaver.scr with Nuitka (onefile, no console window).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$build = Join-Path $root "build"
$dist = Join-Path $root "dist"

& $python -m nuitka `
    --onefile `
    --windows-console-mode=disable `
    --enable-plugins=tk-inter `
    "--onefile-tempdir-spec={CACHE_DIR}/MazeScreensaver/{VERSION}" `
    --product-name="Maze Screensaver" `
    --file-description="Maze Screensaver" `
    --product-version=1.0.0 `
    --file-version=1.0.0 `
    --assume-yes-for-downloads `
    --output-dir="$build" `
    --output-filename=MazeScreensaver.exe `
    (Join-Path $root "MazeScreensaver.py")
if ($LASTEXITCODE -ne 0) { throw "Nuitka build failed with exit code $LASTEXITCODE" }

New-Item -ItemType Directory -Force $dist | Out-Null
Copy-Item (Join-Path $build "MazeScreensaver.exe") (Join-Path $dist "MazeScreensaver.scr") -Force
Write-Output "Built $(Join-Path $dist 'MazeScreensaver.scr')"
