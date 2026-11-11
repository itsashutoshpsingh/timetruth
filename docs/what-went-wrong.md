# What went wrong

Every mismatch class, with a verdict after reading the tool's documentation and, where
needed, its source: **tool bug**, **documented behaviour**, **writer behaviour** or
**my mistake**. Then the misses in my own process.

## Verdicts on the mismatches

| # | What the harness saw | Where | Verdict | Evidence |
|---|---|---|---|---|
| 1 | Every Plaso FAT/exFAT time is 28-31 days late (*wrong value*) | Plaso 20261027 on FAT32 and exFAT, all scenarios, with and without `--timezone` | **Tool bug** (in libfsfat, used by dfVFS) | Raw directory entries decoded by hand, and TSK and mtools, give the true date. `pyfsfat` alone returns month + 1 for 5 dates tested and for 3 libfsfat releases (20240501, 20260208, 20260826). Root cause read in `libfsfat_date_time.c`: three off-by-ones in the day count. The error formula predicts every case. Draft report: `docs/upstream-reports/libfsfat-month-offset.md` |
| 2 | TSK exFAT times off by exactly the offset the writer stored (+5.5 h Kolkata, +1 h London, -4 h New York) without `-z`; and still off by 1 h with the correct `-z` in both DST runs (22 of 22 London, 10 of 22 New York) (*wrong zone*) | TSK 4.12.1 `fls` on exFAT | **Tool limitation, undocumented** | exFAT stores a valid UTC offset next to each time, and the stored pair (wall time, offset) gives the true instant in every run (raw entries decoded by hand). fuse-exfat writes one offset per mount (see `docs/tool-semantics.md`), so around a DST change its wall times are not the legal local time. TSK ignores the offset (`exfatfs_meta.c` declares the fields and never reads them) and re-reads the wall time in the `-z` zone, turning a harmless writer quirk into a wrong time. Draft report: `docs/upstream-reports/tsk-exfat-offset-and-dst.md` |
| 3 | TSK FAT times off by the writer's offset when `-z` is not given (*wrong zone*) | TSK `fls` on FAT32 with the examiner on UTC | **Documented behaviour** | FAT stores local time with no zone. `fls(1)` says to pass `-z` with "the time zone of the original system". The tool cannot know it. The error is the examiner's if `-z` is left out |
| 4 | Same stored wall-clock time decoded to two instants an hour apart in one directory entry (mtime as GMT, crtime as BST) | TSK `fls -z Europe/London` on FAT32, London fall-back run | **Tool bug (minor), reproduced twice** | `fatfs_dos_2_unix_time()` uses `mktime()` with `tm_isdst=-1`; glibc resolves an ambiguous local time using the offset left from its previous call. Draft report, issue 2 |
| 5 | `mactime -d` prints times with no zone; in the repeated hour they cannot be read back (*ambiguous*) | TSK `mactime` on every file system in the London fall-back run | **Documented behaviour, risky** | `mactime(1)`. The `-y` flag prints ISO 8601 UTC with `Z` and avoids it |
| 6 | FAT32 times in the repeated hour (01:00-01:59 local on 25 Oct) are *ambiguous* for every tool | All tools, FAT32 London fall-back | **File-system limitation** | FAT stores local time with no offset; the hour happens twice. No tool can be right except by luck, and none flags it |
| 7 | Plaso lists no deleted exFAT entries (*missing*) where TSK does | Plaso 20261027 on exFAT | **Tool limitation** | TSK `fls` shows the same entries as `(deleted)`. Not investigated further (likely the libfsfat back-end not enumerating deleted entries) |
| 8 | Back-dating with ntfs-3g's `system.ntfs_times` also rewrote `$FILE_NAME`, so no tool could show the true creation time | NTFS forgery set | **Writer behaviour; my wrong assumption** | `istat` shows `$FN` = forged value. On Windows, `SetFileTime` changes only `$SI`, which is the classic tell. My expectation came from Windows. The Windows kit tests the Windows driver |
| 9 | `$MFT`'s own `$SI` times read 2076-11-29 08:54:34 on every image ntfs-3g wrote to | NTFS, all runs (TSK, Plaso and analyzeMFT agree) | **Writer behaviour (ntfs-3g 2022.10.3)** | A fresh `mkntfs` image shows the format time; after ntfs-3g mounts it and writes one file, `istat image 0` shows 2076-11-29 08:54:34 for all four `$SI` times. The tools report what is on disk. It made the clock-anomaly check flag every file until NTFS `$` metadata files were excluded |
| 10 | ext4 files back-dated with `debugfs` (all four times) show no true time anywhere | ext4 forgery set | **Expected** | Offline edit of the inode: nothing left to find in file-system metadata. `touch -d` back-dating still leaves crtime and ctime intact, and every tool shows them |

## Misses in my own process

1. **I first had libfaketime shift `stat()` results too.** The first NTFS smoke run's
   final-state times were 18 days before the truth, because libfaketime also offsets the
   timestamps that `stat()` returns, so the offset was applied twice. Fixed with
   `NO_FAKE_STAT=1`. Caught because the final-state check disagreed with every tool.
2. **I passed `::name` to `mren`.** That moved the renamed FAT file to the root folder, not
   a rename in place. The first FAT run had a file in the wrong place; caught by listing the
   image with `mdir`. Fixed: the new name is now passed bare.
3. **I first checked a file's creation time under its original name.** After a rename,
   every tool reports the creation time under the new name, so the first classifier marked
   correct reports as *not on disk*. Fixed by `resolve_renames()`, with a test.
4. **Coincidental matches.** FAT access times are date-only (midnight). With the run
   starting at exactly 10:00:00, a midnight value was 20 x 30 min away from the first
   action and would have counted as a *wrong zone* match. Runs now start at :07 seconds so
   no action sits on a half-hour boundary.
5. **The guide's 60 s spacing became 12 s** so a DST run fits in 3 minutes either side of
   the change. 12 s is still more than four times the matching tolerance.
6. **MFTECmd did not run.** The release build needs Windows APIs (Mono reports every file as
   "not found"), and building from source was blocked here. analyzeMFT stands in on Linux and
   is labelled as such everywhere. MFTECmd is in the Windows kit.
7. **No real Windows yet.** Every image here was written by a Linux driver. The NTFS and
   exFAT results say how the *tools* read what those drivers wrote. They do not say how
   Windows writes them. That is the Windows kit's job, and it has not been run.
8. **ext4 runs use the real clock.** The kernel ignores libfaketime, so the ext4 "DST"
   runs did not cross a clock change. ext4 stores UTC, so the writer's zone does not
   matter, but the label "london_fall" on an ext4 run only means the writer's `TZ`.
9. **The *not on disk* outcome depends on the tools.** For FAT there is no driver-side
   `stat` (mtools only), so a time no tool reports is counted as not on disk. If every tool
   shared one blind spot it would be hidden. Raw-entry decoding for FAT would close this.
