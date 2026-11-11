#!/usr/bin/env python3
"""Run the 30 scripted actions against one target and write truth.csv (UTC).

Backends:
  posix  - a mounted file system (ext4, ntfs-3g, exfat-fuse); plain os/shutil calls
  mtools - an unmounted FAT image driven by mtools (mtools writes local time from TZ)

Every row records the UTC instant taken immediately before the action and the
host's real UTC time (the run may be under libfaketime; see build/make_run.sh).
"""
import argparse
import csv
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from datetime import datetime, timezone

# (id, type, path, source). Paths are relative to the volume root.
ACTIONS = [
    (1, "mkdir", "/docs", None),
    (2, "mkdir", "/archive", None),
    (3, "create", "/docs/report.txt", None),
    (4, "modify", "/docs/report.txt", None),
    (5, "create", "/docs/notes.txt", None),
    (6, "copy", "/docs/notes_copy.txt", "/docs/notes.txt"),
    (7, "rename", "/docs/notes_v2.txt", "/docs/notes_copy.txt"),
    (8, "move", "/archive/notes_v2.txt", "/docs/notes_v2.txt"),
    (9, "modify", "/docs/report.txt", None),
    (10, "create", "/docs/budget.csv", None),
    (11, "zip", "/archive/budget.zip", "/docs/budget.csv"),
    (12, "delete", "/docs/budget.csv", None),
    (13, "mkdir", "/restored", None),
    (14, "unzip", "/restored/budget.csv", "/archive/budget.zip"),
    (15, "create", "/docs/run.sh", None),
    (16, "access", "/docs/run.sh", None),  # "run a program": the script is read
    (17, "mkdir", "/photos", None),
    (18, "create", "/photos/img001.jpg", None),
    (19, "create", "/photos/img002.jpg", None),
    (20, "rename", "/photos/holiday.jpg", "/photos/img002.jpg"),
    (21, "delete", "/photos/img001.jpg", None),
    (22, "modify", "/docs/notes.txt", None),
    (23, "copy", "/archive/report_backup.txt", "/docs/report.txt"),
    (24, "move", "/restored/notes.txt", "/docs/notes.txt"),
    (25, "create", "/docs/final.txt", None),
    (26, "modify", "/docs/final.txt", None),
    (27, "rename", "/docs/final_v2.txt", "/docs/final.txt"),
    (28, "access", "/archive/report_backup.txt", None),
    (29, "delete", "/archive/budget.zip", None),
    (30, "create", "/done.txt", None),
]


def check_path(action_type, path):
    """Where the action's timestamp should land. A delete leaves no time on the
    file itself; the parent directory's modified time records it."""
    if action_type == "delete":
        return os.path.dirname(path) or "/"
    return path


def utc_iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="microseconds")


def fake_offset():
    """Seconds the faked clock is ahead of the host clock ('+N'/'-N' + 's')."""
    spec = os.environ.get("FAKETIME", "")
    if os.environ.get("LD_PRELOAD", "").find("faketime") < 0 or not spec:
        return 0.0
    assert spec.endswith("s") and spec[0] in "+-", f"unsupported FAKETIME {spec!r}"
    return float(spec[:-1])


class Posix:
    def __init__(self, root):
        self.root = root

    def p(self, path):
        return self.root + path

    def mkdir(self, path, _):
        os.mkdir(self.p(path))

    def create(self, path, _):
        with open(self.p(path), "w") as f:
            f.write(f"created {path}\n")

    def modify(self, path, _):
        with open(self.p(path), "a") as f:
            f.write("modified\n")

    def copy(self, path, src):
        shutil.copyfile(self.p(src), self.p(path))  # content only, no metadata

    def rename(self, path, src):
        os.rename(self.p(src), self.p(path))

    move = rename

    def delete(self, path, _):
        os.remove(self.p(path))

    def zip(self, path, src):
        with zipfile.ZipFile(self.p(path), "w") as z:
            z.write(self.p(src), os.path.basename(src))

    def unzip(self, path, src):
        with zipfile.ZipFile(self.p(src)) as z:
            data = z.read(os.path.basename(path))
        with open(self.p(path), "wb") as f:  # extraction time, not archived time
            f.write(data)

    def access(self, path, _):
        with open(self.p(path), "rb") as f:
            f.read()

    def final_state(self):
        rows = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            for name in dirnames + filenames:
                full = os.path.join(dirpath, name)
                st = os.stat(full, follow_symlinks=False)
                rel = "/" + os.path.relpath(full, self.root)
                # Python 3.13 has no st_birthtime on Linux; GNU stat reads it via statx.
                birth = subprocess.run(["stat", "-c", "%W", full], capture_output=True,
                                       text=True, check=True).stdout.strip()
                birth = None if birth in ("0", "-") else float(birth)
                rows.append((rel, st.st_atime, st.st_mtime, st.st_ctime, birth))
        st = os.stat(self.root)
        rows.append(("/", st.st_atime, st.st_mtime, st.st_ctime, None))
        return rows


class Mtools:
    def __init__(self, image):
        self.image = image
        self.tmp = tempfile.mkdtemp()

    def m(self, *args):
        subprocess.run(list(args[:1]) + ["-i", self.image] + list(args[1:]), check=True,
                       stdout=subprocess.DEVNULL)

    def local(self, name, text):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as f:
            f.write(text)
        return p

    def mkdir(self, path, _):
        self.m("mmd", "::" + path)

    def create(self, path, _):
        self.m("mcopy", self.local("c", f"created {path}\n"), "::" + path)

    def modify(self, path, _):
        p = os.path.join(self.tmp, "mod")
        self.m("mcopy", "-o", "::" + path, p)
        with open(p, "a") as f:
            f.write("modified\n")
        self.m("mcopy", "-o", p, "::" + path)
        os.remove(p)

    def copy(self, path, src):
        p = os.path.join(self.tmp, "cp")
        self.m("mcopy", "-o", "::" + src, p)
        self.m("mcopy", p, "::" + path)
        os.remove(p)

    def rename(self, path, src):
        self.m("mren", "::" + src, os.path.basename(path))  # bare name: "::name" would move it to root

    def move(self, path, src):
        self.m("mmove", "::" + src, "::" + path)

    def delete(self, path, _):
        self.m("mdel", "::" + path)

    def zip(self, path, src):
        p = os.path.join(self.tmp, os.path.basename(src))
        self.m("mcopy", "-o", "::" + src, p)
        zp = os.path.join(self.tmp, "z.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.write(p, os.path.basename(src))
        self.m("mcopy", zp, "::" + path)

    def unzip(self, path, src):
        zp = os.path.join(self.tmp, "u.zip")
        self.m("mcopy", "-o", "::" + src, zp)
        with zipfile.ZipFile(zp) as z:
            data = z.read(os.path.basename(path))
        p = os.path.join(self.tmp, "u")
        with open(p, "wb") as f:
            f.write(data)
        self.m("mcopy", p, "::" + path)

    def access(self, path, _):
        self.m("mtype", "::" + path)

    def final_state(self):
        return []  # shortcut: no driver-side stat for FAT; tools alone decide what survived


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["posix", "mtools"], required=True)
    ap.add_argument("--target", required=True, help="mount point (posix) or image (mtools)")
    ap.add_argument("--out", required=True, help="directory for truth.csv / final_state.csv")
    ap.add_argument("--spacing", type=float, default=12.0)
    args = ap.parse_args()

    backend = Posix(args.target) if args.backend == "posix" else Mtools(args.target)
    off = fake_offset()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "truth.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["action_id", "utc_time", "host_utc_time", "type", "path", "check_path", "source"])
        for i, (aid, kind, path, src) in enumerate(ACTIONS):
            if i:
                time.sleep(args.spacing)
            t = time.time()
            getattr(backend, kind)(path, src)
            w.writerow([aid, utc_iso(t), utc_iso(t - off), kind, path, check_path(kind, path), src or ""])
            f.flush()
    with open(os.path.join(args.out, "final_state.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["path", "atime", "mtime", "ctime", "birthtime"])
        w.writerows(backend.final_state())


if __name__ == "__main__":
    main()
