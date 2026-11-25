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
# the manual and key chart, stamped with the version, beside the patch
python3 tools/manual.py "$VERSION" >/dev/null
cp docs/AmbleLite-manual.pdf docs/AmbleLite-keys.pdf dist/stage/AmbleLite/
cp docs/AmbleLite-manual.pdf docs/AmbleLite-keys.pdf dist/          # (attached to the release on their own too)
git checkout -q -- docs/AmbleLite-manual.pdf docs/AmbleLite-keys.pdf 2>/dev/null || true
(cd dist/stage && zip -qr "../AmbleLite-${VERSION}.zip" .)
rm -rf dist/stage
ls -l dist
