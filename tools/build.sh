#!/bin/bash
# Regenerate patches/AmbleLite from the Python sources:  tools/build.sh [--check]
#   --check  also run the offline checks in Pure Data (tools/check.py)
set -e
cd "$(dirname "$0")"
python3 gen.py
python3 korg.py >/dev/null
python3 planner.py >/dev/null
# (the web editor in the patch folder too: opened from the Organelle's web server it edits that folder's files)
cp ../docs/planner.html ../patches/AmbleLite/planner.html
# the manual and key chart (docs/*.pdf), when reportlab is installed (CI: always)
if python3 -c "import reportlab" 2>/dev/null; then python3 manual.py >/dev/null; else echo "(no reportlab: the PDFs are not rebuilt)"; fi
if [ "$1" = "--check" ]; then
    python3 check.py
fi
