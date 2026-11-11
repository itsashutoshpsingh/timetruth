#!/usr/bin/env bash
# Run every tool configuration on one built image and convert to the common schema.
#   build/run_tools.sh <run>     (e.g. ntfs_london_fall)
# Raw tool output -> $WORK/<run>/raw ; common CSVs -> results/events/<run>/
set -euo pipefail
RUN=$1
HERE=$(cd "$(dirname "$0")/.." && pwd)
source "$HERE/truth/$RUN/run.env"   # FS, ZONE, IMAGE
PY=${PY:-$HERE/.venv/bin/python}
PLASO=${PLASO:-/opt/plaso-venv/bin}
RAW=$(dirname "$IMAGE")/raw; EV=$HERE/results/events/$RUN
rm -rf "$RAW" "$EV"; mkdir -p "$RAW" "$EV"
export TZ=UTC   # the examiner's workstation is on UTC

# The Sleuth Kit: default, then told the writer's zone; mactime display in that zone.
fls -r -m / "$IMAGE" > "$RAW/tsk.body"
fls -z "$ZONE" -r -m / "$IMAGE" > "$RAW/tsk_z.body"
mactime -b "$RAW/tsk_z.body" -z "$ZONE" -d > "$RAW/mactime_z.csv" 2>/dev/null
$PY "$HERE/parse/tsk_to_common.py" body "$RAW/tsk.body" "$EV/tsk_fls.csv" --tool tsk_fls
$PY "$HERE/parse/tsk_to_common.py" body "$RAW/tsk_z.body" "$EV/tsk_fls_z.csv" --tool tsk_fls_z
$PY "$HERE/parse/tsk_to_common.py" mactime "$RAW/mactime_z.csv" "$EV/tsk_mactime_z.csv" --tool tsk_mactime_z --zone "$ZONE"

# Plaso: default, then --timezone set to the writer's zone.
for cfg in plaso plaso_z; do
  extra=(); [ $cfg = plaso_z ] && extra=(--timezone "$ZONE")
  $PLASO/log2timeline --quiet --status_view none --unattended "${extra[@]}" \
      --storage_file "$RAW/$cfg.plaso" "$IMAGE" > "$RAW/$cfg.log" 2>&1
  $PLASO/psort --status_view none -o json_line -w "$RAW/$cfg.jsonl" "$RAW/$cfg.plaso" >> "$RAW/$cfg.log" 2>&1
  $PY "$HERE/parse/plaso_to_common.py" "$RAW/$cfg.jsonl" "$EV/$cfg.csv" --tool $cfg
done

# NTFS only: an independent $MFT parser (MFTECmd cannot run on Linux; see versions.md).
if [ "$FS" = ntfs ]; then
  icat "$IMAGE" 0 > "$RAW/MFT.bin"
  "$(dirname "$PY")/analyzemft" -f "$RAW/MFT.bin" -o "$RAW/analyzemft.csv" --csv > "$RAW/analyzemft.log" 2>&1
  $PY "$HERE/parse/mft_to_common.py" analyzemft "$RAW/analyzemft.csv" "$EV/analyzemft.csv" --tool analyzemft
fi
echo "tools done: $RUN"
