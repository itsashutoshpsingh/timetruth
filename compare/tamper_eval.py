#!/usr/bin/env python3
"""Clock-tamper runs: how far are reported times from real-world time, and does the
allocation-order check flag the files created after the clock was set back?"""
import csv
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import clock_anomaly  # noqa: E402
from diff import load_env, norm_path, resolve_renames  # noqa: E402


def main(out="results/tamper.json"):
    res = {}
    for d in sorted(glob.glob("truth/*_tamper")):
        run = os.path.basename(d)
        env = load_env(os.path.join(d, "run.env"))
        back, first = int(env["CLOCK_SET_BACK_S"]), int(env["TAMPERED_FROM_ACTION"])
        truth = resolve_renames(list(csv.DictReader(open(os.path.join(d, "truth.csv")))))
        created_after = {norm_path(r["check_path"]) for r in truth
                         if int(r["action_id"]) >= first and r["type"] in ("create", "copy", "zip", "unzip", "mkdir")}
        created_before = {norm_path(r["check_path"]) for r in truth
                          if int(r["action_id"]) < first and r["type"] in ("create", "copy", "zip", "unzip", "mkdir")}
        body = os.path.join(os.path.dirname(env["IMAGE"]), "raw", "tsk.body")
        flagged = {norm_path(p.split(" (")[0]): f for p, _, _, f in clock_anomaly.flag(clock_anomaly.load(body))}
        cls = [r for r in csv.DictReader(open("results/classified.csv")) if r["run"] == run]
        res[run] = {
            "actions_after_clock_change": sum(1 for r in truth if int(r["action_id"]) >= first),
            "clock_set_back_hours": back / 3600,
            "outcomes_vs_system_clock": {o: sum(1 for r in cls if r["outcome"] == o)
                                         for o in sorted({r["outcome"] for r in cls})},
            "post_change_files_flagged": sum(1 for p in created_after if flagged.get(p)),
            "post_change_files_seen": sum(1 for p in created_after if p in flagged),
            "pre_change_files_flagged": sum(1 for p in created_before if flagged.get(p)),
            "pre_change_files_seen": sum(1 for p in created_before if p in flagged),
        }
    json.dump(res, open(out, "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
