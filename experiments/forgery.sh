#!/usr/bin/env bash
# Timestamp forgery set: create 5 files, then back-date them to 2020-01-01 with
# the standard methods an ordinary user (or anti-forensic tool) would use, and
# see which tools still expose the true creation time somewhere in their output.
#   experiments/forgery.sh <ntfs|ext4|exfat>
# Methods: ntfs  - rewrite all four $SI times via ntfs-3g's system.ntfs_times xattr
#          ext4  - files 1-3 `touch -d` (a,m only); files 4-5 debugfs offline (a,m,c,cr)
#          exfat - `touch -d` (a,m)
set -euo pipefail
FS=$1
HERE=$(cd "$(dirname "$0")/.." && pwd)
RUN=${FS}_forgery; WORK=${WORK:-/var/tmp/timetruth}/$RUN; OUT=$HERE/truth/$RUN
rm -rf "$WORK" "$OUT"; mkdir -p "$WORK/mnt" "$OUT"
IMG=$WORK/$RUN.img; truncate -s 64M "$IMG"
FORGED=2020-01-01T12:00:00Z; FORGED_S=$(date -u -d $FORGED +%s)
case $FS in
  ntfs) mkntfs -q -F -f -L EVIDENCE "$IMG" >/dev/null 2>&1; ntfs-3g "$IMG" "$WORK/mnt" ;;
  ext4) mkfs.ext4 -q -L EVIDENCE "$IMG"; mount -o loop "$IMG" "$WORK/mnt" ;;
  exfat) mkfs.exfat -L EVIDENCE "$IMG" >/dev/null; LOOP=$(losetup -f --show "$IMG"); mount.exfat-fuse "$LOOP" "$WORK/mnt" ;;
esac
echo "file,true_create_utc,forged_utc,method" > "$OUT/forgery.csv"
for i in 1 2 3 4 5; do
  t=$(date -u +%s.%N); echo "secret $i" > "$WORK/mnt/file$i.txt"
  case $FS in
    ntfs) method=si_all_four_xattr ;;
    ext4) [ $i -le 3 ] && method=touch || method=debugfs_offline ;;
    exfat) method=touch ;;
  esac
  echo "/file$i.txt,$t,$FORGED_S,$method" >> "$OUT/forgery.csv"
  sleep 2
done
sleep 3
ft=$(python3 -c "import struct;print(struct.pack('<Q',($FORGED_S+11644473600)*10**7).hex())")
for i in 1 2 3 4 5; do
  f="$WORK/mnt/file$i.txt"
  case $FS in
    ntfs) setfattr -n system.ntfs_times -v "0x$ft$ft$ft$ft" "$f" ;;
    ext4|exfat) [ "$FS" = exfat ] || [ $i -le 3 ] && touch -d "$FORGED" "$f" || true ;;
  esac
done
umount "$WORK/mnt"; [ "$FS" = exfat ] && losetup -d "$LOOP"
if [ "$FS" = ext4 ]; then
  for i in 4 5; do for fld in atime mtime ctime crtime; do
    debugfs -w -R "set_inode_field /file$i.txt $fld @$FORGED_S" "$IMG" >/dev/null 2>&1
  done; done
fi
sha256sum "$IMG" | awk '{print $1}' > "$OUT/image.sha256"
printf 'FS=%s\nSCENARIO=forgery\nZONE=UTC\nIMAGE=%s\n' "$FS" "$IMG" > "$OUT/run.env"
"$HERE/build/run_tools.sh" "$RUN"
