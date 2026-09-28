# Builds dist\Labyrinth.exe (the game) and dist\Labyrinth.scr (the screensaver) with Nuitka
# (onefile, no console window). Product versions come from versions.json.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$build = Join-Path $root "build"
$dist = Join-Path $root "dist"
$versions = Get-Content (Join-Path $root "versions.json") -Raw | ConvertFrom-Json

# The file version adds a build number that is unique per build: the onefile cache path
# below includes it, so a rebuilt program never reuses stale unpacked files from an
# earlier build of the same product version.
$now = Get-Date
$buildNumber = ($now.Day - 1) * 1440 + $now.Hour * 60 + $now.Minute

function Build-Onefile([string]$entry, [string]$name, [string]$product, [string]$version, [string[]]$extra) {
    & $python -m nuitka `
        --onefile `
        --windows-console-mode=disable `
        "--windows-icon-from-ico=$(Join-Path $root 'packaging\labyrinth.ico')" `
        "--include-data-files=$(Join-Path $root 'maze_saver\assets\icon.png')=maze_saver/assets/icon.png" `
        "--include-data-files=$(Join-Path $root 'versions.json')=labyrinth_update/versions.json" `
        "--onefile-tempdir-spec={CACHE_DIR}/$name/{FILE_VERSION}" `
        --company-name="ByDesign Interactive" `
        --copyright="Copyright $($now.Year) ByDesign Interactive. Licensed under Apache 2.0." `
        --product-name="$product" `
        --file-description="$product" `
        --product-version=$version `
        --file-version="$version.$buildNumber" `
        --assume-yes-for-downloads `
        --output-dir="$build" `
        --output-filename="$name.exe" `
        @extra `
        (Join-Path $root $entry)
    if ($LASTEXITCODE -ne 0) { throw "Nuitka build of $name failed with exit code $LASTEXITCODE" }
}

New-Item -ItemType Directory -Force $dist | Out-Null

Build-Onefile "Labyrinth.py" "Labyrinth" "Labyrinth" $versions.game @()
Copy-Item (Join-Path $build "Labyrinth.exe") (Join-Path $dist "Labyrinth.exe") -Force

Build-Onefile "LabyrinthScreensaver.py" "LabyrinthScreensaver" "Labyrinth Screensaver" $versions.screensaver @("--enable-plugins=tk-inter")
Copy-Item (Join-Path $build "LabyrinthScreensaver.exe") (Join-Path $dist "Labyrinth.scr") -Force

Write-Output "Built $(Join-Path $dist 'Labyrinth.exe') version $($versions.game) and $(Join-Path $dist 'Labyrinth.scr') version $($versions.screensaver) (build $buildNumber)"
