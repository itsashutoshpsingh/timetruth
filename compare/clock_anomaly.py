#!/usr/bin/env python3
"""Flag likely clock changes from allocation order.

File systems hand out new metadata slots (NTFS MFT records, FAT directory-entry
positions) in roughly increasing order, so creation times should mostly increase
with the slot number. A file in a later slot with a creation time much *earlier*
than a file in an earlier slot suggests the clock went backwards. Slots are reused
after deletes, so this is a hint for an examiner, not proof.

Input: a TSK body file. Output: CSV of (path, inode, crtime, flagged).
"""
import argparse
import csv
import re
import sys

THRESHOLD = 3600  # ignore inversions smaller than an hour


def load(body):
    rows = []
    for line in open(body):
        f = line.rstrip("\n").split("|")
        if len(f) < 11 or "($FILE_NAME)" in f[1] or f[10] in ("", "0"):
            continue
        if f[1].startswith("/$"):  # NTFS metadata files: ntfs-3g stamps $MFT with 2076-11-29
            continue
        num = int(re.match(r"\d+", f[2]).group())
        rows.append((num, int(f[10]), f[1]))
    return sorted(rows)


def flag(rows):
    out, latest = [], None
    for num, crtime, path in rows:
        flagged = latest is not None and crtime < latest - THRESHOLD
        out.append((path, num, crtime, flagged))
        latest = crtime if latest is None else max(latest, crtime)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("body")
    ap.add_argument("--out", default="-")
    a = ap.parse_args()
    rows = flag(load(a.body))
    f = sys.stdout if a.out == "-" else open(a.out, "w", newline="")
    w = csv.writer(f)
    w.writerow(["path", "inode", "crtime", "flagged"])
    w.writerows(rows)


if __name__ == "__main__":
    main()
