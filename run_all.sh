#!/usr/bin/env bash
# Regression command: rebuild every image, rerun every tool, reclassify, redraw.
#   ./run_all.sh            full matrix (4 file systems x 4 scenarios, ~35 min)
#   SPACING=1 ./run_all.sh  quick check
set -euo pipefail
cd "$(dirname "$0")"
source build/scenarios.sh
SPACING=${SPACING:-12}
for fs in $FILESYSTEMS; do   # file systems in parallel, scenarios in sequence
  ( for s in $SCENARIOS; do
      build/make_run.sh "$fs" "$s" "$SPACING" && build/run_tools.sh "${fs}_${s}"
    done ) > "logs/$fs.log" 2>&1 &
done
wait
.venv/bin/python compare/diff.py
.venv/bin/python report/summarise.py
.venv/bin/python report/figures.py
