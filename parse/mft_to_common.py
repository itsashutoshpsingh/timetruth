#!/usr/bin/env python3
"""$MFT parser CSV -> common schema.

  analyzemft : analyzeMFT 3.x `--csv`. Its Filepath column comes out empty, so the
               path is rebuilt from Parent Record Number (root = record 5).
  mftecmd    : Eric Zimmerman's MFTECmd `--csv` (for the Windows 11 kit). Times are
               UTC strings like 2026-10-25 00:58:01.7116571.
"""
import argparse
import csv
import sys
from datetime import datetime, timezone

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import norm_path, write  # noqa: E402

AMFT = {"Creation": "b", "Modification": "m", "Access": "a", "Entry": "c"}
MFTECMD = {"Created": "b", "LastModified": "m", "LastAccess": "a", "LastRecordChange": "c"}


def to_epoch(text):
    text = text.strip().rstrip("Z")
    if not text:
        return None
    if "." in text:  # MFTECmd prints 7 fractional digits; datetime takes 6
        head, frac = text.split(".")
        text = f"{head}.{frac[:6]}"
    text = text.replace("T", " ")
    fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in text else "%Y-%m-%d %H:%M:%S"
    return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).timestamp()


def analyzemft_rows(reader, tool):
    recs = list(reader)
    by_id = {r["Record Number"]: r for r in recs}

    def path(r, depth=0):
        parent = r["Parent Record Number"]
        if r["Record Number"] == "5" or depth > 64:
            return ""
        up = by_id.get(parent)
        prefix = "" if parent == "5" or up is None else path(up, depth + 1)
        return f"{prefix}/{r['Filename']}"

    for r in recs:
        if not r["Filename"] or r["Filename"].startswith("$"):
            continue
        p = path(r)
        deleted = int("Valid" not in r["Record Status"] or r.get("Record Type", "").lower().startswith("deleted"))
        for attr, col in (("$SI", "SI"), ("$FN", "FN")):
            for word, kind in AMFT.items():
                t = to_epoch(r.get(f"{col} {word} Time", ""))
                if t:
                    yield dict(tool=tool, path=norm_path(p), epoch=t, kind=kind, attr=attr,
                               deleted=deleted, label_ambiguous=0, raw=r[f"{col} {word} Time"])


def mftecmd_rows(reader, tool):
    for r in reader:
        parent = r["ParentPath"].lstrip(".").replace("\\", "/")
        p = f"{parent}/{r['FileName']}"
        deleted = int(r.get("InUse", "True") == "False")
        for word, kind in MFTECMD.items():
            for attr, suffix in (("$SI", "0x10"), ("$FN", "0x30")):
                t = to_epoch(r.get(word + suffix, ""))
                if t:
                    yield dict(tool=tool, path=norm_path(p), epoch=t, kind=kind, attr=attr,
                               deleted=deleted, label_ambiguous=0, raw=r[word + suffix])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["analyzemft", "mftecmd"])
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--tool", required=True)
    a = ap.parse_args()
    with open(a.infile, newline="", errors="replace") as f:
        reader = csv.DictReader(f)
        rows = analyzemft_rows(reader, a.tool) if a.mode == "analyzemft" else mftecmd_rows(reader, a.tool)
        write(rows, a.outfile)


if __name__ == "__main__":
    main()
