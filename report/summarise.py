#!/usr/bin/env python3
"""Tables and headline numbers from results/classified.csv.

Writes results/tables.md (pasted into the README), results/by_tool.csv,
results/by_fs_tool.csv and results/summary.json (for the portfolio site)."""
import json
import os

import pandas as pd

R = "results"
MATRIX = ["utc", "kolkata", "london_fall", "ny_spring"]
TOOLS = {
    "tsk_fls": "TSK fls 4.12.1 (default)",
    "tsk_fls_z": "TSK fls 4.12.1 -z <writer zone>",
    "tsk_mactime_z": "TSK mactime 4.12.1 -z, -d display",
    "plaso": "Plaso 20261027 (default)",
    "plaso_z": "Plaso 20261027 --timezone <writer zone>",
    "analyzemft": "analyzeMFT 3.1.1 (NTFS only)",
}
SCORED = ["correct", "wrong_zone", "ambiguous", "wrong_value", "missing"]


def table(df, index):
    t = df.pivot_table(index=index, columns="outcome", values="action_id", aggfunc="count", fill_value=0)
    for c in SCORED + ["not_recorded"]:
        if c not in t:
            t[c] = 0
    t = t[SCORED + ["not_recorded"]]
    t["scored"] = t[SCORED].sum(axis=1)
    t["pct_correct"] = (100 * t["correct"] / t["scored"]).round(1)
    return t


def md(t, label):
    cols = ["Correct", "Wrong zone", "Ambiguous", "Wrong value", "Missing", "Not on disk*"]
    lines = [f"| {label} | " + " | ".join(cols) + " | Correct % |", "|" + "---|" * (len(cols) + 2)]
    for idx, r in t.iterrows():
        name = TOOLS.get(idx, idx) if isinstance(idx, str) else " / ".join(map(str, idx))
        vals = [r[c] for c in SCORED + ["not_recorded"]]
        lines.append(f"| {name} | " + " | ".join(str(int(v)) for v in vals) + f" | {r['pct_correct']} |")
    return "\n".join(lines)


def main():
    df = pd.read_csv(os.path.join(R, "classified.csv"))
    m = df[df.scenario.isin(MATRIX)]
    by_tool = table(m, "tool").reindex([t for t in TOOLS if t in set(m.tool)])
    by_fs_tool = table(m, ["fs", "tool"])
    by_fs_scen_tool = table(m, ["fs", "scenario", "tool"])
    by_tool.to_csv(os.path.join(R, "by_tool.csv"))
    by_fs_tool.to_csv(os.path.join(R, "by_fs_tool.csv"))
    by_fs_scen_tool.to_csv(os.path.join(R, "by_fs_scenario_tool.csv"))

    scored = m[m.outcome.isin(SCORED)]
    wrong = scored[scored.outcome != "correct"]
    runs = m.run.nunique()
    counts = wrong.outcome.value_counts().to_dict()
    head = (f"{len(scored)} tool-reported times checked ({runs} runs: {m.fs.nunique()} file systems x "
            f"{m.scenario.nunique()} time-zone scenarios x 30 actions, {m.tool.nunique()} tool configurations). {len(wrong)} ({100 * len(wrong) / len(scored):.0f}%) "
            f"were not the true instant: {counts.get('wrong_value', 0)} wrong value, "
            f"{counts.get('wrong_zone', 0)} right clock reading in the wrong zone, "
            f"{counts.get('ambiguous', 0)} ambiguous, {counts.get('missing', 0)} missing.")

    with open(os.path.join(R, "tables.md"), "w") as f:
        f.write(head + "\n\n")
        f.write(md(by_tool, "Tool (version)") + "\n\n")
        f.write(md(by_fs_tool, "File system / tool") + "\n\n")
        f.write("*Not on disk: no source (the driver's own stat, or any tool) shows the time; "
                "it was never stored or a later action overwrote it. Not counted against tools.\n")

    fs_correct = {fs: round(100 * (g.outcome == "correct").sum() / g.outcome.isin(SCORED).sum(), 1)
                  for fs, g in m.groupby("fs")}
    summary = {
        "project": "timetruth",
        "headline": head,
        "metrics": [
            {"label": "tool-reported times checked", "value": int(len(scored))},
            {"label": "not the true instant", "value": f"{100 * len(wrong) / len(scored):.0f}%"},
            {"label": "wrong value", "value": int(counts.get("wrong_value", 0))},
            {"label": "wrong zone", "value": int(counts.get("wrong_zone", 0))},
            {"label": "ambiguous", "value": int(counts.get("ambiguous", 0))},
            {"label": "missing", "value": int(counts.get("missing", 0))},
        ] + [{"label": f"correct on {fs}", "value": f"{v}%"} for fs, v in sorted(fs_correct.items())],
        "by_tool": {TOOLS.get(k, k): {c: int(v[c]) for c in SCORED + ["not_recorded"]} for k, v in by_tool.iterrows()},
        "charts": ["docs/img/hero_outcomes.png", "docs/img/heatmap_correct.png", "docs/img/dst_offsets.png",
                   "docs/img/pipeline.png"],
    }
    with open(os.path.join(R, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(head)
    print(md(by_tool, "Tool (version)"))


if __name__ == "__main__":
    main()
