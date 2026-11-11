#!/usr/bin/env python3
"""Figures for the README and the portfolio site (dark theme, docs/img/)."""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from summarise import MATRIX, SCORED, TOOLS  # noqa: E402

BG, FG, GRID = "#0b0f14", "#c9d1d9", "#21262d"
COL = {"correct": "#00e5a0", "wrong_zone": "#ffb000", "ambiguous": "#4ea8de",
       "wrong_value": "#ff4d6d", "missing": "#8b949e"}
LABEL = {"correct": "correct", "wrong_zone": "wrong zone", "ambiguous": "ambiguous",
         "wrong_value": "wrong value", "missing": "missing"}
OUT = "docs/img"
plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": BG, "savefig.facecolor": BG, "text.color": FG,
    "axes.labelcolor": FG, "xtick.color": FG, "ytick.color": FG, "axes.edgecolor": GRID,
    "font.family": "monospace", "font.size": 10, "axes.titleweight": "bold",
})


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, name), dpi=200, bbox_inches="tight")
    plt.close(fig)


def hero(m):
    tools = [t for t in TOOLS if t in set(m.tool)]
    s = m[m.outcome.isin(SCORED)]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    left = np.zeros(len(tools))
    for o in SCORED:
        v = np.array([(s[(s.tool == t)].outcome == o).sum() for t in tools])
        tot = np.array([(s.tool == t).sum() for t in tools])
        pct = 100 * v / tot
        ax.barh(range(len(tools)), pct, left=left, color=COL[o], label=LABEL[o], height=0.62)
        for i, (p, l) in enumerate(zip(pct, left)):
            if p >= 7:
                ax.text(l + p / 2, i, f"{p:.0f}%", ha="center", va="center", color=BG, fontsize=9, weight="bold")
        left += pct
    ax.set_yticks(range(len(tools)), [TOOLS[t] for t in tools])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of times each tool reported for the 30 actions (%), all 16 runs")
    ax.legend(ncol=5, loc="lower center", bbox_to_anchor=(0.4, 1.0), frameon=False)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    save(fig, "hero_outcomes.png")


def heatmap(m):
    tools = [t for t in TOOLS if t in set(m.tool)]
    cols = [(fs, sc) for fs in ["ntfs", "ext4", "exfat", "fat32"] for sc in MATRIX]
    s = m[m.outcome.isin(SCORED)]
    grid = np.full((len(tools), len(cols)), np.nan)
    for i, t in enumerate(tools):
        for j, (fs, sc) in enumerate(cols):
            g = s[(s.tool == t) & (s.fs == fs) & (s.scenario == sc)]
            if len(g):
                grid[i, j] = 100 * (g.outcome == "correct").mean()
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("tt", ["#ff4d6d", "#ffb000", "#00e5a0"])
    fig, ax = plt.subplots(figsize=(13, 3.9))
    im = ax.imshow(grid, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    for i in range(len(tools)):
        for j in range(len(cols)):
            v = grid[i, j]
            ax.text(j, i, "n/a" if np.isnan(v) else f"{v:.0f}", ha="center", va="center",
                    color=FG if np.isnan(v) else BG, fontsize=8, weight="bold")
    ax.set_yticks(range(len(tools)), [TOOLS[t] for t in tools])
    ax.set_xticks(range(len(cols)), [sc.replace("_", "\n") for _, sc in cols], fontsize=8)
    for k, fs in enumerate(["NTFS", "ext4", "exFAT", "FAT32"]):
        ax.text(k * 4 + 1.5, -0.9, fs, ha="center", va="bottom", weight="bold", color=FG)
        if k:
            ax.axvline(k * 4 - 0.5, color=BG, lw=3)
    ax.set_title("% of reported times that are the true instant", pad=44)
    cb = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.01)
    cb.outline.set_edgecolor(GRID)
    save(fig, "heatmap_correct.png")


def dst(m):
    d = m[m.delta_s.notna() & (m.delta_s.astype(str) != "")].copy()
    d["delta_s"] = d.delta_s.astype(float)
    d["t"] = pd.to_datetime(d.truth_utc)
    change = {"london_fall": pd.Timestamp("2026-10-25T01:00:00Z"), "ny_spring": pd.Timestamp("2026-03-08T07:00:00Z")}
    styles = {"fat32": ("#ffb000", "o"), "exfat": ("#4ea8de", "s"), "ntfs": ("#00e5a0", "^")}
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3), gridspec_kw={"width_ratios": [1, 1, 1]})
    panels = [("london_fall", "TSK fls -z Europe/London\nclocks go back 02:00 BST -> 01:00 GMT"),
              ("ny_spring", "TSK fls -z America/New_York\nclocks go forward 02:00 EST -> 03:00 EDT")]
    for ax, (sc, title) in zip(axes[:2], panels):
        for fs, (c, mk) in styles.items():
            g = d[(d.tool == "tsk_fls_z") & (d.fs == fs) & (d.scenario == sc)].sort_values("t")
            x = (g.t - change[sc]).dt.total_seconds() / 60
            ax.plot(x, g.delta_s / 3600, marker=mk, ms=4, lw=0, color=c, label=fs)
        ax.axvline(0, color="#ff4d6d", ls="--", lw=1)
        ax.set_ylim(-1.5, 1.5)
        ax.set_title(title, fontsize=9)
        ax.set_xlabel("minutes from the clock change (true time)")
        ax.set_ylabel("reported minus true (hours)")
        ax.grid(color=GRID, lw=0.5)
        ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax = axes[2]
    for fs, (c, mk) in (("fat32", styles["fat32"]), ("exfat", styles["exfat"])):
        g = d[(d.tool == "plaso_z") & (d.fs == fs)]
        ax.hist(g.delta_s / 86400, bins=np.arange(27.5, 32.6, 0.25), color=c, alpha=0.85, label=fs)
    ax.set_title("Plaso 20261027 on FAT32/exFAT, all runs\nlibfsfat day-count error", fontsize=9)
    ax.set_xlabel("reported minus true (days)")
    ax.set_ylabel("tool-reported times")
    ax.grid(color=GRID, lw=0.5)
    ax.legend(frameon=False, fontsize=8)
    save(fig, "dst_offsets.png")


def pipeline():
    steps = [("scripted actions", "30 actions, known UTC\ntimes -> truth.csv"),
             ("writer + fake clock", "ntfs-3g / fuse-exfat /\nmtools / ext4, libfaketime"),
             ("disk image", "64 MB raw, SHA-256\n(not published)"),
             ("tools under test", "TSK fls, mactime,\nPlaso, analyzeMFT"),
             ("common schema", "path, UTC epoch,\nMACB, $SI/$FN"),
             ("classifier", "correct / wrong zone /\nambiguous / wrong value /\nmissing / not on disk")]
    fig, ax = plt.subplots(figsize=(13, 2.4))
    ax.set_xlim(0, len(steps) * 2.2)
    ax.set_ylim(0, 2)
    ax.axis("off")
    for i, (title, body) in enumerate(steps):
        x = i * 2.2 + 0.1
        c = "#00e5a0" if i in (0, 5) else "#ffb000" if i == 3 else "#4ea8de"
        ax.add_patch(FancyBboxPatch((x, 0.2), 1.8, 1.6, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc="#11161d", ec=c, lw=1.6))
        ax.text(x + 0.9, 1.45, title, ha="center", va="center", color=c, weight="bold", fontsize=9)
        ax.text(x + 0.9, 0.8, body, ha="center", va="center", color=FG, fontsize=7.5)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + 2.15, 1.0), xytext=(x + 1.9, 1.0),
                        arrowprops=dict(arrowstyle="->", color=FG, lw=1.4))
    save(fig, "pipeline.png")


def main():
    df = pd.read_csv("results/classified.csv")
    m = df[df.scenario.isin(MATRIX)]
    hero(m)
    heatmap(m)
    dst(m)
    pipeline()
    print("figures ->", OUT)


if __name__ == "__main__":
    main()
