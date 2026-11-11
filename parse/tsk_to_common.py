#!/usr/bin/env python3
"""The Sleuth Kit -> common schema.

  body    : `fls -r -m /` body file (epoch seconds, already converted by TSK)
  mactime : `mactime -b body -z ZONE -d` CSV, which prints local wall-clock time
            with no zone or offset; we convert it back with the zone mactime was
            told to use and flag values that fall in a repeated (DST fall-back) hour.
"""
import argparse
import csv
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import norm_path, write  # noqa: E402

SUFFIX = re.compile(r" \((\$FILE_NAME|deleted|deleted-realloc)\)")


def split_name(name):
    attr = "$FN" if "($FILE_NAME)" in name else ""
    deleted = "(deleted" in name
    return SUFFIX.sub("", name).split(" -> ")[0], attr, deleted


def body_rows(lines, tool):
    for line in lines:
        f = line.rstrip("\n").split("|")
        if len(f) < 11:
            continue
        path, attr, deleted = split_name(f[1])
        for kind, val in zip("amcb", (f[7], f[8], f[9], f[10])):  # atime|mtime|ctime|crtime
            if val and int(val) > 0:
                yield dict(tool=tool, path=norm_path(path), epoch=int(val), kind=kind, attr=attr,
                           deleted=int(deleted), label_ambiguous=0, raw=val)


def local_to_utc(text, zone):
    """Wall-clock text in `zone` -> (epoch, ambiguous). Ambiguous wall times
    (fold) resolve to the first occurrence, as most software does."""
    naive = datetime.strptime(text, "%a %b %d %Y %H:%M:%S")
    tz = ZoneInfo(zone)
    a = naive.replace(tzinfo=tz, fold=0)
    b = naive.replace(tzinfo=tz, fold=1)
    return a.timestamp(), a.utcoffset() != b.utcoffset()


def mactime_rows(lines, tool, zone):
    for r in csv.DictReader(lines):
        date = r["Date"]
        if not date or date.startswith("Xxx"):
            continue
        epoch, amb = local_to_utc(date, zone)
        path, attr, deleted = split_name(r["File Name"])
        for kind in r["Type"].replace(".", ""):
            yield dict(tool=tool, path=norm_path(path), epoch=epoch, kind=kind, attr=attr,
                       deleted=int(deleted), label_ambiguous=int(amb), raw=date)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["body", "mactime"])
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--tool", required=True)
    ap.add_argument("--zone", default="UTC", help="zone mactime displayed in")
    a = ap.parse_args()
    with open(a.infile, errors="replace") as f:
        lines = f.readlines()
    rows = body_rows(lines, a.tool) if a.mode == "body" else mactime_rows(lines, a.tool, a.zone)
    write(rows, a.outfile)


if __name__ == "__main__":
    main()
