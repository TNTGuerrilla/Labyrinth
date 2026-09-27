# Builds dist\MazeGame.exe and dist\MazeScreensaver.scr with Nuitka (onefile, no console window).
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$build = Join-Path $root "build"
$dist = Join-Path $root "dist"

# Unique per build: the onefile cache path below includes the version, so a rebuilt
# program never reuses stale unpacked files from an earlier build.
$now = Get-Date
$buildMinute = ($now.Day - 1) * 1440 + $now.Hour * 60 + $now.Minute
$version = "1.0.$($now.ToString('yyMM')).$buildMinute"

function Build-Onefile([string]$entry, [string]$name, [string]$product, [string[]]$extra) {
    & $python -m nuitka `
        --onefile `
        --windows-console-mode=disable `
        "--onefile-tempdir-spec={CACHE_DIR}/$name/{VERSION}" `
        --product-name="$product" `
        --file-description="$product" `
        --product-version=$version `
        --file-version=$version `
        --assume-yes-for-downloads `
        --output-dir="$build" `
        --output-filename="$name.exe" `
        @extra `
        (Join-Path $root $entry)
    if ($LASTEXITCODE -ne 0) { throw "Nuitka build of $name failed with exit code $LASTEXITCODE" }
}

New-Item -ItemType Directory -Force $dist | Out-Null

Build-Onefile "MazeGame.py" "MazeGame" "Maze Game" @()
Copy-Item (Join-Path $build "MazeGame.exe") (Join-Path $dist "MazeGame.exe") -Force

Build-Onefile "MazeScreensaver.py" "MazeScreensaver" "Maze Screensaver" @("--enable-plugins=tk-inter")
Copy-Item (Join-Path $build "MazeScreensaver.exe") (Join-Path $dist "MazeScreensaver.scr") -Force

Write-Output "Built $(Join-Path $dist 'MazeGame.exe') and $(Join-Path $dist 'MazeScreensaver.scr') version $version"
