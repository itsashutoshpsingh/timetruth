#!/usr/bin/env python3
"""For each forged file and tool: does the output show the forged time, and does
it still show the true creation time anywhere (and in which attribute)?"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "parse"))
from common import norm_path, read  # noqa: E402

TOL = 2.5


def main(truth_root="truth", events_root="results/events", out="results/forgery.csv"):
    rows = []
    for d in sorted(glob.glob(os.path.join(truth_root, "*_forgery"))):
        run = os.path.basename(d)
        forged = list(csv.DictReader(open(os.path.join(d, "forgery.csv"))))
        for p in sorted(glob.glob(os.path.join(events_root, run, "*.csv"))):
            tool = os.path.basename(p)[:-4]
            ev = list(read(p))
            for fr in forged:
                path = norm_path(fr["file"])
                mine = [e for e in ev if e["path"] == path]
                true_t, fake_t = float(fr["true_create_utc"]), float(fr["forged_utc"])
                shows_true = [e for e in mine if abs(e["epoch"] - true_t) <= TOL]
                rows.append(dict(run=run, fs=run.split("_")[0], tool=tool, file=fr["file"], method=fr["method"],
                                 reports_forged=int(any(abs(e["epoch"] - fake_t) <= TOL for e in mine)),
                                 shows_true_time=int(bool(shows_true)),
                                 via=" ".join(sorted({(e["attr"] or "-") + ":" + e["kind"] for e in shows_true}))))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
