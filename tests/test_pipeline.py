import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(HERE)
FX = os.path.join(HERE, "fixtures")
sys.path[:0] = [os.path.join(ROOT, "parse"), os.path.join(ROOT, "compare")]

import diff  # noqa: E402
import mft_to_common  # noqa: E402
import plaso_to_common  # noqa: E402
import tsk_to_common  # noqa: E402
from common import norm_path  # noqa: E402


def test_norm_path():
    assert norm_path("NTFS:\\Docs\\Report.TXT") == "/docs/report.txt"
    assert norm_path("FAT:\\") == "/"


def test_body_order_and_suffixes():
    rows = list(tsk_to_common.body_rows(open(os.path.join(FX, "sample.body")), "t"))
    si = {r["kind"]: r["epoch"] for r in rows if r["path"] == "/docs/report.txt" and not r["attr"]}
    assert si == {"a": 1792889880, "m": 1792889881, "c": 1792889882, "b": 1792889883}
    assert any(r["attr"] == "$FN" for r in rows)
    deleted = [r for r in rows if r["path"] == "/docs/budget.csv"]
    assert deleted and all(r["deleted"] for r in deleted) and {r["kind"] for r in deleted} == {"m", "c", "b"}


def test_mactime_flags_repeated_hour():
    rows = list(tsk_to_common.mactime_rows(open(os.path.join(FX, "sample_mactime.csv")), "t", "Europe/London"))
    amb = {r["kind"]: r["label_ambiguous"] for r in rows}
    assert amb == {"m": 1, "b": 1, "a": 0}     # 01:58 happens twice on 25 Oct; 03:10 once
    first = [r for r in rows if r["kind"] == "m"][0]
    assert first["epoch"] == 1792889880          # fold=0: the BST reading, 00:58 UTC


def test_plaso_rows():
    rows = list(plaso_to_common.rows(open(os.path.join(FX, "sample_plaso.jsonl")), "p"))
    assert len(rows) == 2                         # registry event ignored
    assert rows[1]["path"] == "/docs/report.txt" and rows[1]["attr"] == "$FN" and rows[1]["kind"] == "b"
    assert rows[0]["epoch"] == pytest.approx(1792889881.432261)


def test_analyzemft_rebuilds_paths():
    import csv
    rows = list(mft_to_common.analyzemft_rows(csv.DictReader(open(os.path.join(FX, "sample_analyzemft.csv"))), "a"))
    paths = {r["path"] for r in rows}
    assert "/docs/report.txt" in paths and "/docs" in paths
    m = [r for r in rows if r["path"] == "/docs/report.txt" and r["attr"] == "$SI" and r["kind"] == "m"][0]
    assert m["epoch"] == pytest.approx(1792889822.638)


def test_mftecmd_layout():
    import csv
    rows = list(mft_to_common.mftecmd_rows(csv.DictReader(open(os.path.join(FX, "sample_mftecmd.csv"))), "z"))
    assert {r["path"] for r in rows} == {"/docs/report.txt"}
    assert {(r["attr"], r["kind"]) for r in rows} == {("$SI", "b"), ("$FN", "b"), ("$SI", "m"), ("$SI", "c"), ("$SI", "a")}


def test_repeated_hour():
    assert diff.in_repeated_hour(1792891807, "Europe/London")       # 01:30 GMT on 25 Oct
    assert not diff.in_repeated_hour(1792843200, "Europe/London")   # 13:00 BST on 24 Oct
    assert not diff.in_repeated_hour(1792891807, "Asia/Kolkata")


def test_classifier_outcomes():
    rows = diff.classify_run(os.path.join(FX, "run_demo"), os.path.join(FX, "events_demo", "run_demo"))
    got = {(r["tool"], r["action_id"]): r["outcome"] for r in rows}
    assert got[("good", "1")] == "correct"
    assert got[("good", "4")] == "correct"        # create d.txt, found under its renamed name e.txt
    assert got[("good", "5")] == "not_recorded"   # FAT keeps no rename time
    assert got[("good", "6")] == "ambiguous"      # stored local time in the repeated hour
    assert got[("bad", "1")] == "wrong_zone"
    assert got[("bad", "2")] == "wrong_value"
    assert got[("bad", "3")] == "missing"
    assert got[("bad", "6")] == "missing"
    assert set(r["outcome"] for r in rows) <= set(diff.OUTCOMES)


def test_action_list_is_thirty_and_ordered():
    sys.path.insert(0, os.path.join(ROOT, "actions"))
    import run_actions
    ids = [a[0] for a in run_actions.ACTIONS]
    assert ids == list(range(1, 31))
    assert run_actions.check_path("delete", "/docs/x.txt") == "/docs"


def test_cli_smoke(tmp_path):
    out = tmp_path / "c.csv"
    subprocess.run([sys.executable, os.path.join(ROOT, "compare", "diff.py"), "--truth", FX,
                    "--events", os.path.join(FX, "events_demo"), "--out", str(out)], check=True)
    assert out.read_text().count("\n") == 1 + 6 * 2


def test_clock_anomaly_flags_backwards_jump(tmp_path):
    import clock_anomaly
    body = tmp_path / "b.body"
    body.write_text("\n".join([
        "0|/a|10-128-2|r|0|0|1|0|0|0|1000000",
        "0|/b|11-128-2|r|0|0|1|0|0|0|1000100",
        "0|/b ($FILE_NAME)|11-48-3|r|0|0|1|0|0|0|1",   # $FN lines ignored
        "0|/c|12-128-2|r|0|0|1|0|0|0|827300",          # 2 days earlier: clock set back
        "0|/d|13-128-2|r|0|0|1|0|0|0|998000",          # earlier by < 1 h: not flagged
    ]) + "\n")
    flags = {p: f for p, _, _, f in clock_anomaly.flag(clock_anomaly.load(str(body)))}
    assert flags == {"/a": False, "/b": False, "/c": True, "/d": False}
