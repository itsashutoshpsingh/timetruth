"""Common event schema shared by every converter.

One row per (path, timestamp) a tool reports:
  tool, path, epoch (UTC seconds, float), kind (m/a/c/b), attr (e.g. $SI/$FN),
  deleted (0/1), label_ambiguous (0/1: the tool printed a local time that maps to
  two instants), raw (the tool's own text for the value)
"""
import csv

FIELDS = ["tool", "path", "epoch", "kind", "attr", "deleted", "label_ambiguous", "raw"]


def norm_path(p):
    """Tools disagree on separators, prefixes and case; compare on a normal form."""
    p = p.replace("\\", "/")
    for prefix in ("NTFS:", "FAT:", "EXT:", "TSK:", "EXFAT:"):
        if p.startswith(prefix):
            p = p[len(prefix):]
    if not p.startswith("/"):
        p = "/" + p
    return p.rstrip("/").lower() or "/"


def write(rows, out_path):
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def read(path):
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            r["epoch"] = float(r["epoch"])
            r["deleted"] = r["deleted"] == "1"
            r["label_ambiguous"] = r["label_ambiguous"] == "1"
            yield r
