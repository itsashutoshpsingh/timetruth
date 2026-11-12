# Upstream report: exFAT UTC offset fields are ignored, and DST-ambiguous FAT times resolve to different instants within one entry

**Status: ready to file, not yet filed.** Open a new issue at https://github.com/sleuthkit/sleuthkit/issues/new with the title above and everything below the line as the body. No existing report was found when searching the tracker on 2026-11-12.

---

## Versions

- The Sleuth Kit 4.12.1 (Ubuntu 4.12.1+dfsg-1.1ubuntu2), glibc 2.39
- source read at sleuthkit/sleuthkit `08167c8d6d5fc1bd4ee6d822e2fe042cabcdee6d` (2026-11-10)

## Issue 1: exFAT `*_time_zone_offset` fields are parsed but never used

exFAT file directory entries store, next to each local timestamp, a UTC offset in
15-minute units with a valid bit (exFAT spec 7.4.10-7.4.12). `tsk_exfatfs.h`
declares `created_time_time_zone_offset`, `modified_time_time_zone_offset` and
`accessed_time_time_zone_offset`, but `exfatfs_meta.cpp` converts all three times with
`fatfs_dos_2_unix_time()` and never reads the offsets. The stored local time is then
interpreted in the examiner's `-z` zone (or `TZ`).

Reproduce (timetruth run `exfat_kolkata`): a volume written by fuse-exfat 1.4.0
with `TZ=Asia/Kolkata` stores 15:30:07 local with offset byte 0x96 (valid, +5:30).
`fls -r -m /` on a UTC workstation reports 15:30:07 UTC, 5.5 h late; `fls -z
Asia/Kolkata` is right only because the examiner happened to know the writer's zone.
The offset on disk would have made the answer correct with no `-z` at all.

Suggested fix: when bit 7 of the offset byte is set, compute UTC as the local time minus
the signed 7-bit offset x 15 min and skip the `mktime()` path; fall back to the current
behaviour only when the offset is not valid.

## Issue 2: one wall-clock time, two different instants, in the same entry

For FAT and exFAT, `fatfs_dos_2_unix_time()` sets `tm_isdst = -1` and calls
`mktime()`. For a local time in the repeated hour after clocks go back, glibc's
`mktime()` picks one of the two possible instants based on the offset it cached from
its previous call. TSK converts a directory entry's fields one after another, so two
fields holding the same wall-clock value come out an hour apart.

Reproduce (twice, same result each time):

```bash
truncate -s 40M amb.img && mkfs.vfat -F 32 amb.img
FAKETIME="@2026-10-25 00:58:00" TZ=Europe/London \
  LD_PRELOAD=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1 mcopy -i amb.img some.txt ::/a.txt
fls -z Europe/London -r -m / amb.img | grep a.txt
# mtime 1792893480 (01:58 GMT)  crtime 1792889880 (01:58 BST = the true instant)
```

Both fields store `2026-10-25 01:58:00`. The body file gives them different epochs, and
`mactime -d` then prints both as `Sun Oct 25 2026 01:58:00`, with no zone, so a reader
cannot see that they differ by an hour.

Suggested fix: flag the value as ambiguous (TSK has no field for that today), or at
least resolve every field of an entry the same way (always the first occurrence, as
Python's `fold=0` does), and document it in `fls(1)`'s `-z` description.

## Not a bug, but worth a line in the docs

`fls -z` is documented as "the time zone of the original system". On exFAT the
original system already wrote its offset to disk, and on NTFS/ext4 `-z` has no effect.
Saying which file systems `-z` applies to would stop examiners relying on it for the
wrong ones.

Found with [timetruth](https://github.com/itsashutoshpsingh/timetruth), a ground-truth test harness for forensic timeline tools. Happy to split this into two issues if you prefer.
