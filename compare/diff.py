#!/usr/bin/env python3
"""Join each truth row to each tool configuration's events and classify it.

Outcomes, per (run, tool, action):
  correct      a reported time for the action's path is within TOL of the truth
  wrong_zone   no correct time, but one is off by a whole number of half hours
               (the right wall-clock reading in the wrong zone)
  ambiguous    the value cannot be pinned to one instant: the tool printed a local
               time with no offset that occurs twice (DST fall-back), or the evidence
               itself stores local time with no offset (FAT) inside a repeated hour
  wrong_value  the action's time survives on disk (the driver's own stat, or another
               tool, shows it) and this tool reports the path, but with no matching time
  missing      the action's time survives on disk but the tool reports nothing for
               the path at all
  not_recorded no source shows the time: the file system never stored it or a later
               action overwrote it. Not counted against any tool.
"""
import argparse
import csv
import glob
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "parse"))
from common import norm_path, read  # noqa: E402

TOL = 2.5                        # FAT stores modified time in 2 s steps (truncated)
SHIFTS = [k * 1800 for k in range(-28, 29) if k]   # +-14 h in half hours
LOCAL_NO_OFFSET = {"fat32"}      # exFAT stores an offset; ext4/NTFS store UTC
OUTCOMES = ["correct", "wrong_zone", "ambiguous", "wrong_value", "missing", "not_recorded"]


def epoch(iso):
    return datetime.fromisoformat(iso).timestamp()


def in_repeated_hour(ts, zone):
    """True if the wall-clock reading of instant `ts` in `zone` happens twice."""
    tz = ZoneInfo(zone)
    wall = datetime.fromtimestamp(ts, tz).replace(tzinfo=None)
    return wall.replace(tzinfo=tz, fold=0).utcoffset() != wall.replace(tzinfo=tz, fold=1).utcoffset()


def load_env(path):
    with open(path) as f:
        return dict(line.rstrip("\n").split("=", 1) for line in f if "=" in line)


def survives_on_disk(final_rows, path, t):
    for r in final_rows:
        if norm_path(r["path"]) == path:
            for k in ("atime", "mtime", "ctime", "birthtime"):
                if r[k] and abs(float(r[k]) - t) <= TOL:
                    return True
    return False


def resolve_renames(truth):
    """A file's earlier times travel with it when it is renamed or moved, so check
    them under the name it ends up with (e.g. create img002.jpg -> holiday.jpg)."""
    for i, row in enumerate(truth):
        if row["type"] in ("rename", "move"):
            for earlier in truth[:i]:
                if earlier["type"] != "delete" and earlier["check_path"] == row["source"]:
                    earlier["check_path"] = row["path"]
    return truth


def match(events, t):
    """Best match of truth instant t among events: (kind, delta, event)."""
    near = [e for e in events if abs(e["epoch"] - t) <= TOL]
    if near:
        return "near", min(near, key=lambda e: abs(e["epoch"] - t))
    for e in events:
        d = e["epoch"] - t
        for s in SHIFTS:
            if abs(d - s) <= TOL:
                return "shift", e
    return None, None


def classify_run(truth_dir, events_dir):
    env = load_env(os.path.join(truth_dir, "run.env"))
    fs, zone = env["FS"], env["ZONE"]
    with open(os.path.join(truth_dir, "truth.csv")) as f:
        truth = resolve_renames(list(csv.DictReader(f)))
    final_path = os.path.join(truth_dir, "final_state.csv")
    final = list(csv.DictReader(open(final_path))) if os.path.exists(final_path) else []

    tools = {}
    for p in sorted(glob.glob(os.path.join(events_dir, "*.csv"))):
        by_path = {}
        for e in read(p):
            by_path.setdefault(e["path"], []).append(e)
        tools[os.path.basename(p)[:-4]] = by_path

    first = {}   # per action: what each tool matched, before deciding survival
    for row in truth:
        t, path = epoch(row["utc_time"]), norm_path(row["check_path"])
        for tool, by_path in tools.items():
            first[(row["action_id"], tool)] = (match(by_path.get(path, []), t), path in by_path)

    out = []
    for row in truth:
        aid, t, path = row["action_id"], epoch(row["utc_time"]), norm_path(row["check_path"])
        source_ambiguous = fs in LOCAL_NO_OFFSET and in_repeated_hour(t, zone)
        seen_by_some_tool = any(first[(aid, tl)][0][0] for tl in tools)
        survives = seen_by_some_tool or survives_on_disk(final, path, t)
        for tool in tools:
            (how, e), has_path = first[(aid, tool)]
            delta = round(e["epoch"] - t, 3) if e else ""
            reason = ""
            if how and (source_ambiguous or e["label_ambiguous"]):
                outcome = "ambiguous"
                reason = "stored local time in repeated hour" if source_ambiguous else "printed local time in repeated hour"
            elif how == "near":
                outcome = "correct"
            elif how == "shift":
                outcome, reason = "wrong_zone", f"off by {delta / 3600:+.1f} h"
            elif not survives:
                outcome, reason = "not_recorded", "no source shows this time"
            elif has_path:
                outcome = "wrong_value"
                ev = tools[tool][path]
                nearest = min(ev, key=lambda x: abs(x["epoch"] - t))
                delta = round(nearest["epoch"] - t, 3)
                reason = f"nearest reported time off by {delta / 86400:+.2f} d"
            else:
                outcome, reason = "missing", "path not reported"
            out.append(dict(run=os.path.basename(truth_dir), fs=fs, scenario=env["SCENARIO"], zone=zone,
                            tool=tool, action_id=aid, type=row["type"], check_path=row["check_path"],
                            truth_utc=row["utc_time"], outcome=outcome, delta_s=delta,
                            kind=e["kind"] if e else "", attr=e["attr"] if e else "", reason=reason))
    return out


FIELDS = ["run", "fs", "scenario", "zone", "tool", "action_id", "type", "check_path", "truth_utc",
          "outcome", "delta_s", "kind", "attr", "reason"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth", default="truth")
    ap.add_argument("--events", default="results/events")
    ap.add_argument("--out", default="results/classified.csv")
    a = ap.parse_args()
    rows = []
    for d in sorted(glob.glob(os.path.join(a.truth, "*"))):
        ev = os.path.join(a.events, os.path.basename(d))
        if os.path.isdir(ev) and os.path.exists(os.path.join(d, "truth.csv")):
            rows += classify_run(d, ev)
    with open(a.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} classifications -> {a.out}")


if __name__ == "__main__":
    main()
