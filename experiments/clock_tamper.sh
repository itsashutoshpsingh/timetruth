#!/usr/bin/env bash
# Clock tampering: actions 1-15 run with a correct clock, then the system clock
# is set back 2 days (the volume is remounted, as a reboot would) and actions
# 16-30 run. Tools can only report the clock that stamped the disk; the question
# is whether anything in their output lets an examiner see the jump.
#   experiments/clock_tamper.sh <ntfs|fat32>
set -euo pipefail
FS=$1
HERE=$(cd "$(dirname "$0")/.." && pwd)
RUN=${FS}_tamper; WORK=${WORK:-/var/tmp/timetruth}/$RUN; OUT=$HERE/truth/$RUN
rm -rf "$WORK" "$OUT"; mkdir -p "$WORK/mnt" "$OUT"
IMG=$WORK/$RUN.img; truncate -s 64M "$IMG"
LIB=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1
ZONE=UTC; START=2026-11-02T14:00:07Z; BACK=172800
O1=$(( $(date -u -d "$START" +%s) - $(date -u +%s) )); O2=$(( O1 - BACK ))
ACT="python3 $HERE/actions/run_actions.py --out $OUT --spacing ${SPACING:-12}"
seg() {  # seg <offset> <ids>
  local off; off=$(printf '%+ds' "$1")
  if [ "$FS" = ntfs ]; then
    TZ=$ZONE FAKETIME=$off NO_FAKE_STAT=1 LD_PRELOAD=$LIB ntfs-3g "$IMG" "$WORK/mnt"
    TZ=$ZONE FAKETIME=$off NO_FAKE_STAT=1 LD_PRELOAD=$LIB $ACT --backend posix --target "$WORK/mnt" --ids "$2"
    umount "$WORK/mnt"
  else
    TZ=$ZONE FAKETIME=$off NO_FAKE_STAT=1 LD_PRELOAD=$LIB $ACT --backend mtools --target "$IMG" --ids "$2"
  fi
}
# Format on the same (correct) clock as the first segment, as the owner's machine would.
F1=$(printf '%+ds' "$O1"); FK="env TZ=$ZONE FAKETIME=$F1 NO_FAKE_STAT=1 LD_PRELOAD=$LIB"
case $FS in ntfs) $FK mkntfs -q -F -f -L EVIDENCE "$IMG" >/dev/null 2>&1 ;; fat32) $FK mkfs.vfat -F 32 -n EVIDENCE "$IMG" >/dev/null ;; esac
seg "$O1" 1-15
seg "$O2" 16-30
sha256sum "$IMG" | awk '{print $1}' > "$OUT/image.sha256"
printf 'FS=%s\nSCENARIO=tamper\nZONE=%s\nSTART=%s\nCLOCK_SET_BACK_S=%s\nTAMPERED_FROM_ACTION=16\nIMAGE=%s\n' \
  "$FS" "$ZONE" "$START" "$BACK" "$IMG" > "$OUT/run.env"
"$HERE/build/run_tools.sh" "$RUN"
