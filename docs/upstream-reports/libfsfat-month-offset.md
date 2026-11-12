# Upstream report: FAT/exFAT timestamps are 28 to 31 days late: off-by-one errors in libfsfat_date_time_get_timestamp()

**Status: ready to file, not yet filed.** Open a new issue at https://github.com/libyal/libfsfat/issues/new with the title above and everything below the line as the body. No existing report was found when searching the tracker on 2026-11-12.

---

## Summary

`libfsfat_date_time_get_timestamp()` returns every FAT and exFAT date and time
between 28 and 31 days too late. Plaso uses libfsfat through dfVFS for FAT and
exFAT volumes, so every FAT/exFAT file-system timestamp in a Plaso timeline is
shifted by roughly a month.

## Versions

- libfsfat-python 20260826 (PyPI); also seen in 20240501 and 20260208
- source read at libyal/libfsfat `7bf92e028617049e57fbe752b8019fd453d509ad` (2026-11-09)
- Plaso 20261027, dfVFS 20260924

## Reproduce

```bash
truncate -s 40M d.img && mkfs.vfat -F 32 d.img
# write a file whose directory entry says 2025-02-28 12:00:00
FAKETIME="@2025-02-28 12:00:00" TZ=UTC LD_PRELOAD=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1 \
  mcopy -i d.img some.txt ::/a.txt
python3 -c "import pyfsfat; v=pyfsfat.volume(); v.open('d.img'); print(v.get_file_entry_by_path('\\\\a.txt').get_modification_time())"
# 2025-03-28 12:00:00   (on-disk entry, TSK fls and mtools mdir all say 2025-02-28)
```

Decoded raw directory entries next to libfsfat output (5 dates):

| On disk (decoded by hand) | libfsfat 20260826 |
|---|---|
| 2026-01-15 12:00:00 | 2026-02-15 12:00:00 |
| 2026-07-01 12:00:00 | 2026-08-01 12:00:00 |
| 2026-10-25 00:57:00 | 2026-11-25 00:57:00 |
| 2026-12-31 12:00:00 | 2027-01-31 12:00:00 |
| 2025-02-28 12:00:00 | 2025-03-28 12:00:00 |

## Cause

In `libfsfat/libfsfat_date_time.c` the day count since 1980-01-01 is built as:

```c
safe_fat_timestamp = day_of_month;          /* should be day_of_month - 1 */
while( month > 0 ) { add days in `month`; month--; }   /* adds the current month too */
while( year > 1980 ) { add days in `year`; year--; }   /* adds the current year, not 1980 */
```

Three off-by-ones:

1. the day of month is 1-based but is added as elapsed days (+1 day);
2. the month loop adds the days of the current month as well as the earlier ones (+28 to +31);
3. the year loop counts years `year .. 1981` instead of `1980 .. year-1`, which only
   matters when exactly one of 1980 and `year` is a leap year (-1 day in a common year).

Net error = days-in-month(month) + 1 - (1 if `year` is not a leap year else 0). This
predicts all five rows above exactly: for example, January 2026 gives 31 + 1 - 1 = 31 days.

## Suggested fix

```c
safe_fat_timestamp = day_of_month - 1;
for( m = 1; m < month; m++ )  add days in m (leap-aware for February of `year`);
for( y = 1980; y < year; y++ ) add 365 or 366;
```

plus a unit test in `tests/` for a few known dates (there is no date-time test today).

## Impact

Any timeline of a FAT or exFAT volume (USB sticks, SD cards, camera media) built
with Plaso 20261027 places every file-system event about a month late. TSK and the
operating system show the correct date, so the error is easy to miss unless two tools
are compared.

Found with [timetruth](https://github.com/itsashutoshpsingh/timetruth), a ground-truth test harness for forensic timeline tools; the full runs and classification are in that repository.
