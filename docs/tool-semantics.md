# What each tool says each time means

Two tools can both be right and still disagree, because they report different
things. Read this before calling any difference an error.

## What the file systems store (as written by the drivers used here)

| File system | Times stored | Zone | Resolution | Notes from these runs |
|---|---|---|---|---|
| NTFS | `$SI`: created, modified, MFT changed, accessed. `$FN`: the same four, per name | UTC (FILETIME) | 100 ns | ntfs-3g updates `$FN` together with `$SI`, including when back-dating through `system.ntfs_times`. The Windows driver does not do this |
| ext4 | atime, mtime, ctime, crtime | UTC (epoch) | 1 ns | default `relatime`; ctime cannot be set by `touch` |
| exFAT | created, modified, accessed | **local time + UTC offset** (15-min units, valid bit) | 10 ms (c, m), 2 s (a) | fuse-exfat 1.4.0 writes **one offset per mount**: 0x96 (+5:30) Kolkata; 0x84 (+1:00) for the whole London run, even after clocks went back; 0xF0 (-4:00) for the whole New York run, even before clocks went forward. Wall time and offset always agree on the true UTC instant, so the instant is recoverable even when the wall time is not the legal local time |
| FAT32 | created, modified, accessed (date only) | **local time, no offset** | 10 ms (c), 2 s (m), 1 day (a) | mtools 4.0.43 uses `TZ` for local time. A rename or move changes no time on the file |

## What each tool reports

| Tool | Output time base | MACB letters / fields | Zone handling |
|---|---|---|---|
| TSK `fls -m` (body file) | epoch seconds | atime, mtime, ctime (NTFS: MFT changed; ext4: inode change), crtime | FAT/exFAT local times converted with `mktime()` in `-z` zone or `TZ`. exFAT offset ignored. NTFS `$FN` shown as a second `($FILE_NAME)` line |
| TSK `mactime -d` | wall-clock text, **no zone** | `m`, `a`, `c`, `b` | printed in `-z` zone; a time in a repeated hour cannot be read back unambiguously |
| Plaso `psort -o json_line` | microseconds UTC | `Content Modification`, `Last Access`, `Metadata Modification`, `Creation` | `--timezone` applies to values without an indicator (FAT); exFAT offset honoured by libfsfat. NTFS: `filestat` ($SI) **and** `mft` parser ($SI + $FN, with `attribute_type` 16/48) |
| analyzeMFT 3.1.1 | ISO 8601 UTC, ms | `SI`/`FN` x Creation, Modification, Access, Entry | none needed (NTFS is UTC) |
| MFTECmd (Windows kit) | UTC text, 100 ns | `Created`, `LastModified`, `LastRecordChange`, `LastAccess` x `0x10` ($SI) / `0x30` ($FN) | none needed |

## Matching rule used by `compare/diff.py`

A truth row is matched against **any** of the times a tool reports for the action's
path, whatever its MACB letter, because the question is "does the tool show when this
happened?" rather than "does it call it the same name?". The matched letter and
attribute are saved in `results/classified.csv` (`kind`, `attr`), so the semantic
question can be answered separately. For example, on ext4 a rename is visible only as
ctime, while on NTFS it is visible as the `$SI` MFT-changed time and the new `$FN`.

## Things that look like errors but are not

- **A rename or move on FAT leaves no time.** Every tool agrees. Outcome: *not on disk*.
- **A delete leaves no time on the deleted file.** Its parent folder's modified time
  records it, until the next change in that folder overwrites it.
- **Access times.** FAT stores a date only (local midnight). ext4 updates atime under
  `relatime` only when the old atime is older than mtime/ctime or more than a day old.
- **Copy.** `shutil.copyfile` / `[IO.File]::WriteAllBytes` copy content only, so the
  copy's created and modified times are the copy time. Explorer copies keep the source's
  modified time, which is a different action.
- **Unzip.** Python's `zipfile` and .NET's `ZipFile` write the extraction time. `unzip`
  and Explorer restore the archived modified time, which in a ZIP is local time with no
  zone: the same trap as FAT.
