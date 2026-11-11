#!/usr/bin/env python3
"""Plaso psort `-o json_line` -> common schema.

`timestamp` is microseconds since 1970 UTC as Plaso stored it. File-system
events come from the `filestat` parser; NTFS also yields `mft` parser events
whose `filename` is \\$MFT and whose real path is in `path_hints`.
"""
import argparse
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from common import norm_path, write  # noqa: E402

KIND = {
    "Content Modification Time": "m",
    "Last Access Time": "a",
    "Metadata Modification Time": "c",
    "Creation Time": "b",
}


def rows(lines, tool):
    for line in lines:
        e = json.loads(line)
        kind = KIND.get(e.get("timestamp_desc"))
        if not kind or not e.get("data_type", "").startswith("fs:stat"):
            continue
        path = e.get("filename", "")
        if path == "\\$MFT" and e.get("path_hints"):
            path = e["path_hints"][0]
        attr = {16: "$SI", 48: "$FN"}.get(e.get("attribute_type"), "")
        yield dict(tool=tool, path=norm_path(path), epoch=e["timestamp"] / 1e6, kind=kind,
                   attr=attr, deleted=int(e.get("is_allocated") is False), label_ambiguous=0,
                   raw=e["timestamp"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--tool", required=True)
    a = ap.parse_args()
    with open(a.infile) as f:
        write(rows(f, a.tool), a.outfile)


if __name__ == "__main__":
    main()
