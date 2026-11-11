#!/usr/bin/env bash
# Build one evidence image: make a file system, run the 30 actions at a chosen
# (faked) start time in a chosen time zone, unmount, hash.
#   build/make_run.sh <ntfs|exfat|fat32|ext4> <scenario> [spacing_seconds]
# Scenarios are defined in build/scenarios.sh.
set -euo pipefail
FS=$1; SCEN=$2; SPACING=${3:-12}
HERE=$(cd "$(dirname "$0")/.." && pwd)
source "$HERE/build/scenarios.sh"
scenario "$SCEN"   # sets ZONE and START (UTC ISO, or "now")

RUN="${FS}_${SCEN}"
WORK=${WORK:-/var/tmp/timetruth}/$RUN
OUT=$HERE/truth/$RUN
rm -rf "$WORK" "$OUT"; mkdir -p "$WORK/mnt" "$OUT"
IMG=$WORK/$RUN.img
truncate -s 64M "$IMG"

LIB=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1
fake() {  # run "$@" with the shared faked clock (constant offset from host time)
  if [ -n "${OFFSET:-}" ]; then TZ=$ZONE FAKETIME="$OFFSET" NO_FAKE_STAT=1 LD_PRELOAD=$LIB "$@"; else TZ=$ZONE "$@"; fi
}
if [ "$START" != now ]; then
  d=$(( $(date -u -d "$START" +%s) - $(date -u +%s) ))
  OFFSET=$(printf '%+ds' "$d")
fi

ACT="python3 $HERE/actions/run_actions.py --out $OUT --spacing $SPACING"
case $FS in
  ntfs)
    mkntfs -q -F -f -L EVIDENCE "$IMG" >/dev/null 2>&1
    fake ntfs-3g "$IMG" "$WORK/mnt"
    fake $ACT --backend posix --target "$WORK/mnt"
    umount "$WORK/mnt" ;;
  exfat)
    mkfs.exfat -L EVIDENCE "$IMG" >/dev/null
    LOOP=$(losetup -f --show "$IMG")
    fake mount.exfat-fuse "$LOOP" "$WORK/mnt"
    fake $ACT --backend posix --target "$WORK/mnt"
    umount "$WORK/mnt"; losetup -d "$LOOP" ;;
  fat32)
    mkfs.vfat -F 32 -n EVIDENCE "$IMG" >/dev/null
    fake $ACT --backend mtools --target "$IMG" ;;
  ext4)
    mkfs.ext4 -q -L EVIDENCE "$IMG"
    mount -o loop "$IMG" "$WORK/mnt"
    TZ=$ZONE $ACT --backend posix --target "$WORK/mnt"
    umount "$WORK/mnt" ;;
  *) echo "unknown fs $FS" >&2; exit 2 ;;
esac

sha256sum "$IMG" | awk '{print $1}' > "$OUT/image.sha256"
cat > "$OUT/run.env" <<EOF
FS=$FS
SCENARIO=$SCEN
ZONE=$ZONE
START=$START
OFFSET=${OFFSET:-0}
SPACING=$SPACING
IMAGE=$IMG
BUILT_HOST_UTC=$(date -u +%FT%TZ)
EOF
echo "built $RUN -> $IMG"
