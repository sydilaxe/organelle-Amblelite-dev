#!/bin/bash
# Package the patch for a release:  tools/package.sh VERSION   ->  dist/AmbleLite-VERSION.zip
# (saves.txt, pieces.txt and roadmap.txt are left out: copying a new version over the old one keeps yours)
set -e
cd "$(dirname "$0")/.."
VERSION="${1:-dev}"
rm -rf dist && mkdir -p dist/stage
cp -r patches/AmbleLite dist/stage/
rm -f dist/stage/AmbleLite/saves.txt dist/stage/AmbleLite/pieces.txt dist/stage/AmbleLite/roadmap.txt dist/stage/AmbleLite/controllers/user.txt
printf 'Amble Lite %s\n' "$VERSION" > dist/stage/AmbleLite/VERSION.txt
(cd dist/stage && zip -qr "../AmbleLite-${VERSION}.zip" .)
rm -rf dist/stage
ls -l dist
