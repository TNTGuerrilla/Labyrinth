#!/bin/sh
# Builds the Linux release of Labyrinth (the game) with Nuitka: a onefile program, packed with its
# app-menu entry, icon and installer into dist/Labyrinth-<version>-linux-x86_64.tar.gz.
# The version comes from versions.json. Set PYTHON to pick the interpreter (default python3);
# it needs requirements-dev.txt installed, and the system needs gcc and patchelf.
set -eu

root=$(cd "$(dirname "$0")" && pwd)
python=${PYTHON:-python3}
build=$root/build
dist=$root/dist
app_id=com.bydesigninteractive.labyrinth
version=$("$python" -c "import json, sys; print(json.load(open(sys.argv[1]))['game'])" "$root/versions.json")

# A build number unique per build, as in build.ps1: the onefile cache path includes it, so a
# rebuilt program never reuses stale unpacked files from an earlier build of the same version.
build_number=$(( ($(date +%-d) - 1) * 1440 + $(date +%-H) * 60 + $(date +%-M) ))

"$python" -m nuitka \
    --onefile \
    "--onefile-tempdir-spec={CACHE_DIR}/Labyrinth/$version.$build_number" \
    --include-data-files="$root/maze_saver/assets/icon.png=maze_saver/assets/icon.png" \
    --include-data-files="$root/versions.json=labyrinth_update/versions.json" \
    --linux-icon="$root/maze_saver/assets/icon.png" \
    --assume-yes-for-downloads \
    --output-dir="$build" \
    --output-filename=Labyrinth \
    "$root/Labyrinth.py"

package=Labyrinth-$version-linux-x86_64
stage=$build/$package
rm -rf "$stage"
mkdir -p "$stage" "$dist"
install -m 755 "$build/Labyrinth" "$stage/Labyrinth"
install -m 755 "$root/packaging/linux/install.sh" "$stage/install.sh"
install -m 644 "$root/packaging/linux/$app_id.desktop" "$stage/$app_id.desktop"
install -m 644 "$root/maze_saver/assets/icon.png" "$stage/$app_id.png"
install -m 644 "$root/LICENSE" "$root/NOTICE" "$stage/"
tar -czf "$dist/$package.tar.gz" -C "$build" "$package"

echo "Built $dist/$package.tar.gz (build $build_number)"
