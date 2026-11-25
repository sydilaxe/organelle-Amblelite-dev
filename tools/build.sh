#!/bin/bash
# Regenerate patches/AmbleLite from the Python sources:  tools/build.sh [--check]
#   --check  also run the offline checks in Pure Data (tools/check.py)
set -e
cd "$(dirname "$0")"
python3 gen.py
python3 planner.py >/dev/null
if [ "$1" = "--check" ]; then
    python3 check.py
fi
